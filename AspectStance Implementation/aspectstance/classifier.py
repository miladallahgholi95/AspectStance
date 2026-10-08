"""Aspect-conditioned stance model (Section 4.6, Eqs. 9-11).

The input of training post i is  z_i = [v_i ; onehot(c_i)] in R^(40 + K_T)  (Eq. 9). The predictor
is a soft-voting ensemble of KNN, XGBoost and a random forest, all at library defaults; the three
class-probability distributions are averaged with equal weight and the argmax is returned (Eq. 10).
The Base Method uses the same ensemble on v alone.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np


def one_hot(clusters: np.ndarray, k: int) -> np.ndarray:
    """One-hot encoding of cluster indices in {0, ..., k-1}: clusters are unordered categories."""
    clusters = np.asarray(clusters, dtype=np.int64)
    if clusters.size and (clusters.min() < 0 or clusters.max() >= k):
        raise ValueError(f"Cluster indices must lie in [0, {k})")
    encoded = np.zeros((len(clusters), k), dtype=np.float64)
    encoded[np.arange(len(clusters)), clusters] = 1.0
    return encoded


def with_cluster_feature(
    v: np.ndarray,
    clusters: np.ndarray,
    k: int,
    column_order: Optional[Sequence[int]] = None,
) -> np.ndarray:
    """Eq. (9): concatenate the unnormalised representation with the one-hot cluster block.

    ``column_order`` permutes the one-hot columns (used by the invariance check only).
    """
    block = one_hot(clusters, k)
    if column_order is not None:
        block = block[:, list(column_order)]
    return np.hstack([np.asarray(v, dtype=np.float64), block])


def default_members(random_state: Optional[int] = None) -> List[Tuple[str, object]]:
    """KNN, XGBoost and random forest at their library defaults.

    Only the random forest draws on the seed: KNN and XGBoost are deterministic given their input
    (Section 5.4). XGBoost is pinned to one thread so that results do not depend on the number of
    parallel jobs; the thread count does not change the model.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.neighbors import KNeighborsClassifier
    from xgboost import XGBClassifier

    return [
        ("knn", KNeighborsClassifier()),
        ("xgboost", XGBClassifier(n_jobs=1)),
        ("random_forest", RandomForestClassifier(random_state=random_state)),
    ]


class SoftVotingEnsemble:
    """Equal-weight soft voting over KNN, XGBoost and a random forest (Eq. 10)."""

    def __init__(self, random_state: Optional[int] = None):
        self.random_state = random_state
        self.classes_: Optional[np.ndarray] = None
        self.members_: List[Tuple[str, object]] = []

    def fit(self, X: np.ndarray, y: Sequence[str]) -> "SoftVotingEnsemble":
        from sklearn.preprocessing import LabelEncoder

        encoder = LabelEncoder().fit(np.asarray(y))
        self.classes_ = encoder.classes_
        y_encoded = encoder.transform(np.asarray(y))
        if len(self.classes_) < 2:
            raise ValueError("At least two stance labels are needed to train the ensemble")
        self.members_ = []
        for name, estimator in default_members(self.random_state):
            estimator.fit(np.asarray(X, dtype=np.float64), y_encoded)
            self.members_.append((name, estimator))
        return self

    def member_probabilities(self, X: np.ndarray) -> List[np.ndarray]:
        """p_m(. | z) of every member, columns aligned with ``classes_``."""
        if self.classes_ is None:
            raise RuntimeError("SoftVotingEnsemble must be fitted first")
        X = np.asarray(X, dtype=np.float64)
        n_classes = len(self.classes_)
        out = []
        for _, estimator in self.members_:
            proba = np.asarray(estimator.predict_proba(X), dtype=np.float64)
            aligned = np.zeros((len(X), n_classes))
            aligned[:, np.asarray(estimator.classes_, dtype=np.int64)] = proba
            out.append(aligned)
        return out

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """(1/3) * sum_m p_m(y | z)."""
        return np.mean(self.member_probabilities(X), axis=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.classes_[self.predict_proba(X).argmax(axis=1)]
