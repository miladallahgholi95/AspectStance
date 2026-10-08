"""Contextual representation (Section 4.3, Eqs. 6-7).

A single UMAP mapping U is fitted per target on the embeddings of the *training posts only* and
then frozen. It gives the reduced coordinates of the training posts, and projects the gloss
embeddings of the training posts and, at inference, both embeddings of each new post, so that the
two reduced views share one coordinate system:

    r = U(e),   r~ = U(e~),   v = [r; r~] in R^40.

The stance classifier receives the unnormalised v; only clustering and routing use v / ||v||.
"""

from __future__ import annotations

import warnings
from typing import Optional

import numpy as np


def l2_normalise(matrix: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Row-wise L2 normalisation, Eq. (8):  v^ = v / ||v||_2."""
    matrix = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, eps)


class SharedUMAP:
    """The frozen per-target mapping U shared by the post and gloss views."""

    def __init__(
        self,
        n_components: int = 20,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = "cosine",
        random_state: Optional[int] = None,
    ):
        self.n_components = n_components
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.metric = metric
        self.random_state = random_state
        self.reducer_ = None
        self.train_post_coords_: Optional[np.ndarray] = None

    def fit(self, post_embeddings: np.ndarray) -> "SharedUMAP":
        """Fit U on the training-post embeddings of one target (no gloss, no test post)."""
        import umap

        post_embeddings = np.asarray(post_embeddings, dtype=np.float32)
        n_neighbors = min(self.n_neighbors, len(post_embeddings) - 1)
        self.reducer_ = umap.UMAP(
            n_components=self.n_components,
            n_neighbors=n_neighbors,
            min_dist=self.min_dist,
            metric=self.metric,
            random_state=self.random_state,
        )
        with warnings.catch_warnings():
            # "n_jobs value 1 overridden to 1 by setting random_state" -- expected for seeded runs.
            warnings.filterwarnings("ignore", message=".*n_jobs value.*", category=UserWarning)
            self.train_post_coords_ = np.asarray(
                self.reducer_.fit_transform(post_embeddings), dtype=np.float64
            )
        return self

    def _project(self, embeddings: np.ndarray) -> np.ndarray:
        if self.reducer_ is None:
            raise RuntimeError("SharedUMAP must be fitted first")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            return np.asarray(
                self.reducer_.transform(np.asarray(embeddings, dtype=np.float32)), dtype=np.float64
            )

    def training_representation(self, gloss_embeddings: np.ndarray) -> np.ndarray:
        """v for the training posts: fitted post coordinates + out-of-sample gloss projection."""
        if self.train_post_coords_ is None:
            raise RuntimeError("SharedUMAP must be fitted first")
        if len(gloss_embeddings) != len(self.train_post_coords_):
            raise ValueError("One gloss embedding per training post is required")
        return np.hstack([self.train_post_coords_, self._project(gloss_embeddings)])

    def transform(self, post_embeddings: np.ndarray, gloss_embeddings: np.ndarray) -> np.ndarray:
        """v for new posts: both views projected with the frozen mapping."""
        if len(post_embeddings) != len(gloss_embeddings):
            raise ValueError("post and gloss embeddings must be row-aligned")
        return np.hstack([self._project(post_embeddings), self._project(gloss_embeddings)])
