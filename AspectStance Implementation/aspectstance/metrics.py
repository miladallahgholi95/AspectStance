"""Evaluation metric (Section 5.2).

``F1_avg`` (Eq. 14) is the mean of the FAVOR and AGAINST F1 scores, the official SemEval-2016
Task 6 metric, also used for P-Stance. NONE is excluded from the average, but NONE posts stay in
the evaluation: predicting FAVOR or AGAINST for them lowers the precision of the predicted class.

``F-macro_T`` (reported in the paper) averages F1_avg over targets with equal weight;
``F-micro_T`` (the official SemEval ranking) pools all predictions before scoring.
All scores are on a 0-100 scale.
"""

from __future__ import annotations

from typing import Dict, Iterable, Sequence

import numpy as np


def f1_avg(y_true: Sequence[str], y_pred: Sequence[str]) -> Dict[str, float]:
    """Return ``{'f1_favor', 'f1_against', 'f1_avg'}`` in percent."""
    from sklearn.metrics import f1_score

    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    favor, against = f1_score(
        y_true, y_pred, labels=["FAVOR", "AGAINST"], average=None, zero_division=0
    )
    return {
        "f1_favor": 100.0 * float(favor),
        "f1_against": 100.0 * float(against),
        "f1_avg": 100.0 * float(favor + against) / 2.0,
    }


def f_macro_t(per_target_scores: Iterable[float]) -> float:
    """Equal-weight mean of per-target F1_avg values."""
    scores = list(per_target_scores)
    if not scores:
        raise ValueError("No per-target scores given")
    return float(np.mean(scores))


def f_micro_t(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """F1_avg computed on predictions pooled across targets."""
    return f1_avg(y_true, y_pred)["f1_avg"]
