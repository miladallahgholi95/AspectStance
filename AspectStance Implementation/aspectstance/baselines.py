"""Prompting baselines (Section 5.3, Appendix A.2 and A.3).

* **Zero-shot** -- GPT-6 Luna is asked for the stance of each test post, with no examples.
* **Retrieval-augmented few-shot** -- for each test post and *each* label, the five training posts
  of the same target and that label whose ``text-embedding-3-large`` embeddings are most similar
  (cosine) to the test post are added to the prompt: 15 examples for SemEval-2016, 10 for P-Stance.

Neither baseline has a seed of its own, so the test split is passed through each one ten times and
the mean over passes is reported. Each pass has its own cache namespace, so the passes are
independent calls rather than cached repeats.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .llm import LLMClient
from .metrics import f1_avg
from .prompts import few_shot_prompt, format_examples, parse_label, render, zero_shot_prompt
from .representation import l2_normalise

INVALID = "INVALID"


def label_set(frame: pd.DataFrame) -> Tuple[str, ...]:
    """Ternary when the dataset has a NONE class (SemEval-2016), binary otherwise (P-Stance)."""
    return ("FAVOR", "AGAINST", "NONE") if (frame["label"] == "NONE").any() else ("FAVOR", "AGAINST")


def balanced_neighbours(
    test_vectors: np.ndarray,
    train_vectors: np.ndarray,
    train_labels: Sequence[str],
    labels: Sequence[str],
    per_label: int = 5,
) -> List[List[int]]:
    """Indices of the ``per_label`` most similar training posts of every label, per test post.

    Examples are grouped by label (in ``labels`` order), most similar first within each label.
    """
    train_labels = np.asarray(train_labels, dtype=object)
    similarity = l2_normalise(test_vectors) @ l2_normalise(train_vectors).T
    per_test: List[List[int]] = [[] for _ in range(len(test_vectors))]
    for label in labels:
        candidates = np.flatnonzero(train_labels == label)
        if candidates.size == 0:
            continue
        take = min(per_label, candidates.size)
        order = np.argsort(-similarity[:, candidates], axis=1, kind="stable")[:, :take]
        for i in range(len(test_vectors)):
            per_test[i].extend(candidates[order[i]].tolist())
    return per_test


def build_prompts(
    frame: pd.DataFrame,
    mode: str,
    post_embeddings: Optional[np.ndarray] = None,
    per_label: int = 5,
) -> pd.DataFrame:
    """One prompt per test post; returns ``id, target, label, prompt``."""
    labels = label_set(frame)
    rows = []
    for target in sorted(frame["target"].unique()):
        test_mask = ((frame["target"] == target) & (frame["split"] == "test")).to_numpy()
        test = frame[test_mask]
        if mode == "zero-shot":
            template = zero_shot_prompt(labels)
            prompts = [render(template, tweet=t, target=target) for t in test["text"]]
        elif mode == "few-shot":
            if post_embeddings is None:
                raise ValueError("The few-shot baseline needs the post embeddings for retrieval")
            train_mask = ((frame["target"] == target) & (frame["split"] == "train")).to_numpy()
            train = frame[train_mask]
            neighbours = balanced_neighbours(
                post_embeddings[test_mask], post_embeddings[train_mask], train["label"], labels, per_label
            )
            template = few_shot_prompt(labels)
            train_texts, train_labels = train["text"].tolist(), train["label"].tolist()
            prompts = []
            for text, idx in zip(test["text"], neighbours):
                examples = format_examples((train_texts[j], target, train_labels[j]) for j in idx)
                prompts.append(render(template, tweet=text, target=target, examples=examples))
        else:
            raise ValueError("mode must be 'zero-shot' or 'few-shot'")
        rows.append(
            pd.DataFrame({"id": test["id"], "target": target, "label": test["label"], "prompt": prompts})
        )
    return pd.concat(rows, ignore_index=True)


def run_prompting_baseline(
    frame: pd.DataFrame,
    mode: str,
    llm: LLMClient,
    passes: int = 10,
    post_embeddings: Optional[np.ndarray] = None,
    per_label: int = 5,
    progress: bool = True,
) -> pd.DataFrame:
    """Run ``passes`` passes over the test split; returns one row per (pass, test post)."""
    prompts = build_prompts(frame, mode, post_embeddings, per_label)
    labels = label_set(frame)
    out = []
    for p in range(passes):
        responses = llm.complete_many(
            prompts["prompt"].tolist(), namespace=f"{mode}/pass{p}", desc=f"{mode} pass {p + 1}/{passes}",
            progress=progress,
        )
        parsed = [parse_label(r, labels) or INVALID for r in responses]
        out.append(
            prompts[["id", "target", "label"]].assign(pass_index=p, response=responses, prediction=parsed)
        )
    return pd.concat(out, ignore_index=True)


def score_prompting(predictions: pd.DataFrame) -> pd.DataFrame:
    """Per-pass, per-target F1_avg."""
    rows = []
    for (p, target), group in predictions.groupby(["pass_index", "target"]):
        rows.append({"pass_index": p, "target": target, **f1_avg(group["label"], group["prediction"])})
    return pd.DataFrame(rows)
