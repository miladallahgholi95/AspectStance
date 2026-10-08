"""The per-target AspectStance predictor f_T (Sections 4.3-4.7).

Training (one target, its training split only)::

    e, e~  --U (fitted on e)-->  v = [r; r~]  --L2-->  v^  --K-means, K by silhouette-->  c
    ensemble( [v ; onehot(c)] , y )

Inference (frozen U, frozen centroids, trained ensemble)::

    e, e~  --U-->  v  --L2-->  v^  --nearest centroid (Eq. 12)-->  k*
    y^ = ensemble( [v ; onehot(k*)] )            (Eq. 13)

Each prediction is returned with the index of the aspect cluster that conditioned it.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np

from .classifier import SoftVotingEnsemble, with_cluster_feature
from .clustering import NearestCentroidRouter, SilhouetteSweep, silhouette_sweep
from .config import ClusteringConfig, UMAPConfig
from .representation import SharedUMAP, l2_normalise


@dataclass
class Prediction:
    labels: np.ndarray
    clusters: np.ndarray
    probabilities: np.ndarray
    classes: np.ndarray
    aspect_names: Optional[Sequence[Optional[str]]] = None


class AspectStanceModel:
    """Aspect-conditioned stance model for one target.

    Parameters
    ----------
    target:
        Name of the stance target (for bookkeeping only).
    umap_config, clustering_config:
        Paper defaults when omitted (20 components, 15 neighbours, min_dist 0.1, cosine; K=2..30).
    random_state:
        Seed of the run; it drives UMAP, K-means and the random forest.
    use_cluster_feature:
        ``False`` gives the Base Method: same representation and ensemble, no one-hot block.
    """

    def __init__(
        self,
        target: str = "",
        umap_config: Optional[UMAPConfig] = None,
        clustering_config: Optional[ClusteringConfig] = None,
        random_state: Optional[int] = None,
        use_cluster_feature: bool = True,
    ):
        self.target = target
        self.umap_config = umap_config or UMAPConfig()
        self.clustering_config = clustering_config or ClusteringConfig()
        self.random_state = random_state
        self.use_cluster_feature = use_cluster_feature
        self.aspect_names: Dict[int, str] = {}

    # ------------------------------------------------------------------------------------------
    # training
    # ------------------------------------------------------------------------------------------
    def fit(
        self,
        post_embeddings: np.ndarray,
        gloss_embeddings: np.ndarray,
        labels: Sequence[str],
    ) -> "AspectStanceModel":
        labels = np.asarray(labels, dtype=object)
        if not (len(post_embeddings) == len(gloss_embeddings) == len(labels)):
            raise ValueError("posts, glosses and labels must be row-aligned")

        self.representation_ = SharedUMAP(
            **dataclasses.asdict(self.umap_config), random_state=self.random_state
        ).fit(post_embeddings)
        v = self.representation_.training_representation(gloss_embeddings)
        self.train_representation_ = v

        if self.use_cluster_feature:
            c = self.clustering_config
            self.sweep_: Optional[SilhouetteSweep] = silhouette_sweep(
                l2_normalise(v),
                k_min=c.k_min,
                k_max=c.k_max,
                metric=c.silhouette_metric,
                random_state=self.random_state,
            )
            self.router_: Optional[NearestCentroidRouter] = NearestCentroidRouter(self.sweep_.centroids)
            self.train_clusters_: Optional[np.ndarray] = self.sweep_.labels
            features = with_cluster_feature(v, self.train_clusters_, self.sweep_.k)
        else:
            self.sweep_, self.router_, self.train_clusters_ = None, None, None
            features = v

        self.ensemble_ = SoftVotingEnsemble(random_state=self.random_state).fit(features, labels)
        return self

    # ------------------------------------------------------------------------------------------
    # inference
    # ------------------------------------------------------------------------------------------
    @property
    def n_aspects(self) -> int:
        return 0 if self.sweep_ is None else self.sweep_.k

    @property
    def silhouette(self) -> Optional[float]:
        return None if self.sweep_ is None else self.sweep_.silhouette

    def represent(self, post_embeddings: np.ndarray, gloss_embeddings: np.ndarray) -> np.ndarray:
        """v = [U(e); U(e~)] with the frozen mapping."""
        return self.representation_.transform(post_embeddings, gloss_embeddings)

    def route(self, v: np.ndarray) -> np.ndarray:
        """Eq. (12): nearest frozen centroid of the L2-normalised representation."""
        if self.router_ is None:
            raise RuntimeError("The Base Method has no aspect inventory")
        return self.router_.route(l2_normalise(v))

    def predict_representation(self, v: np.ndarray) -> Prediction:
        """Predict from an already computed representation v (Eq. 13)."""
        clusters = self.route(v) if self.use_cluster_feature else np.full(len(v), -1)
        features = (
            with_cluster_feature(v, clusters, self.n_aspects) if self.use_cluster_feature else v
        )
        proba = self.ensemble_.predict_proba(features)
        labels = self.ensemble_.classes_[proba.argmax(axis=1)]
        names = None
        if self.aspect_names:
            names = [self.aspect_names.get(int(c)) for c in clusters]
        return Prediction(labels, clusters, proba, self.ensemble_.classes_, names)

    def predict(self, post_embeddings: np.ndarray, gloss_embeddings: np.ndarray) -> Prediction:
        """Stance label + routed aspect index for new posts of this target."""
        return self.predict_representation(self.represent(post_embeddings, gloss_embeddings))

    # ------------------------------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------------------------------
    def save(self, path: str | Path) -> Path:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @staticmethod
    def load(path: str | Path) -> "AspectStanceModel":
        import joblib

        model = joblib.load(path)
        if not isinstance(model, AspectStanceModel):
            raise TypeError(f"{path} does not contain an AspectStanceModel")
        return model
