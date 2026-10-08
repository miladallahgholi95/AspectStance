"""Target-specific aspect discovery and routing (Sections 4.4, 4.7 and the random control of 5.3).

* K-means runs on the L2-normalised training representations, for which squared Euclidean distance
  equals 2 - 2 cos(theta), so nearest-centroid assignment approximates spherical K-means.
* Every K in {2, ..., 30} is evaluated and the partition with the highest *cosine* silhouette
  coefficient is retained; its centroids are frozen.
* A held-out post is routed to the nearest frozen centroid, Eq. (12):
  k*(x) = argmin_k || v^ - mu_k ||_2.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np


@dataclass
class SilhouetteSweep:
    """Result of the per-target inventory-size sweep."""

    k: int
    silhouette: float
    labels: np.ndarray
    centroids: np.ndarray
    scores: Dict[int, float] = field(default_factory=dict)

    @property
    def sizes(self) -> np.ndarray:
        return np.bincount(self.labels, minlength=self.k)


def silhouette_sweep(
    vhat: np.ndarray,
    k_min: int = 2,
    k_max: int = 30,
    metric: str = "cosine",
    random_state: Optional[int] = None,
) -> SilhouetteSweep:
    """Fit K-means for every K in [k_min, k_max] and keep the highest-silhouette partition.

    K-means runs with the scikit-learn defaults (k-means++ initialisation, ``n_init='auto'``);
    only ``random_state`` is set, to the seed of the run. Ties are resolved towards the smaller K.
    """
    from sklearn.cluster import KMeans
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.metrics import silhouette_score

    vhat = np.asarray(vhat, dtype=np.float64)
    n = len(vhat)
    k_max = min(k_max, n - 1)
    if k_max < k_min:
        raise ValueError(f"Need more than {k_min} posts to cluster (got {n})")

    best = None
    scores: Dict[int, float] = {}
    for k in range(k_min, k_max + 1):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            model = KMeans(n_clusters=k, random_state=random_state).fit(vhat)
        labels = model.labels_
        if np.unique(labels).size < 2:
            score = -1.0  # silhouette is undefined for a single cluster
        else:
            score = float(silhouette_score(vhat, labels, metric=metric))
        scores[k] = score
        if best is None or score > best[0]:
            best = (score, k, labels.copy(), model.cluster_centers_.copy())

    score, k, labels, centroids = best  # type: ignore[misc]
    return SilhouetteSweep(k=k, silhouette=score, labels=labels, centroids=centroids, scores=scores)


class NearestCentroidRouter:
    """Frozen centroids and the routing rule of Eq. (12).

    Centroids of empty clusters (possible only for random partitions) may be ``NaN``; they are
    never selected.
    """

    def __init__(self, centroids: np.ndarray):
        self.centroids = np.asarray(centroids, dtype=np.float64)

    @property
    def n_clusters(self) -> int:
        return len(self.centroids)

    def distances(self, vhat: np.ndarray) -> np.ndarray:
        vhat = np.asarray(vhat, dtype=np.float64)
        diff = vhat[:, None, :] - self.centroids[None, :, :]
        dist = np.sqrt(np.einsum("nkd,nkd->nk", diff, diff))
        return np.where(np.isnan(dist), np.inf, dist)

    def route(self, vhat: np.ndarray, chunk_size: int = 4096) -> np.ndarray:
        vhat = np.asarray(vhat, dtype=np.float64)
        out = np.empty(len(vhat), dtype=np.int64)
        for start in range(0, len(vhat), chunk_size):
            out[start : start + chunk_size] = self.distances(vhat[start : start + chunk_size]).argmin(axis=1)
        return out


def random_partition(n: int, k: int, rng: np.random.Generator) -> np.ndarray:
    """Uniformly random assignment of n training posts to k clusters (random-clustering control)."""
    return rng.integers(0, k, size=n)


def centroids_from_labels(vhat: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    """Mean L2-normalised representation of each cluster; ``NaN`` rows for empty clusters."""
    vhat = np.asarray(vhat, dtype=np.float64)
    centroids = np.full((k, vhat.shape[1]), np.nan)
    for cluster in range(k):
        members = labels == cluster
        if members.any():
            centroids[cluster] = vhat[members].mean(axis=0)
    return centroids
