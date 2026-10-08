"""Benchmark loading (Section 5.1).

Everything downstream works on one *canonical* table with the columns

    id, dataset, target, split, text, label

``split`` is ``train``, ``val`` or ``test``; ``label`` is ``FAVOR``, ``AGAINST`` or ``NONE``.

Supported inputs
----------------
* **P-Stance** (Li et al., 2021): ``raw_{train,val,test}_{trump,biden,bernie}.csv`` with the columns
  ``Tweet, Target, Stance``. The validation split is not used for training, model selection or
  evaluation, as in the paper, so it is skipped by default.
* **SemEval-2016 Task 6, Subtask A** (Mohammad et al., 2016): the official tab-separated files
  (``ID  Target  Tweet  Stance``), or any CSV / XLSX export with the same columns. Pass the trial
  file together with the training file to reproduce the paper's training split
  ("its official training data, including the 100 trial posts").

Tweet texts are not redistributed with this repository; obtain them from the original releases.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

CANONICAL_COLUMNS = ["id", "dataset", "target", "split", "text", "label"]
LABELS = ("FAVOR", "AGAINST", "NONE")
#: The two classes averaged by the official metric F1_avg (Eq. 14).
SCORED_LABELS = ("FAVOR", "AGAINST")

PSTANCE_TARGETS: Dict[str, str] = {
    "trump": "Donald Trump",
    "biden": "Joe Biden",
    "bernie": "Bernie Sanders",
}

SEMEVAL_SUBTASK_A_TARGETS = (
    "Atheism",
    "Climate Change is a Real Concern",
    "Feminist Movement",
    "Hillary Clinton",
    "Legalization of Abortion",
)

#: Short display names used in the paper's tables.
DISPLAY_NAMES: Dict[str, str] = {
    "Donald Trump": "Trump",
    "Joe Biden": "Biden",
    "Bernie Sanders": "Sanders",
    "Climate Change is a Real Concern": "Climate Change",
}

_LABEL_ALIASES = {
    "FAVOR": "FAVOR",
    "FAVOUR": "FAVOR",
    "AGAINST": "AGAINST",
    "NONE": "NONE",
    "NEUTRAL": "NONE",
}


def display_name(target: str) -> str:
    return DISPLAY_NAMES.get(target, target)


def slugify(text: str) -> str:
    """File-system friendly version of a target name."""
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def normalise_label(value: object) -> str:
    key = str(value).strip().upper()
    if key not in _LABEL_ALIASES:
        raise ValueError(f"Unknown stance label: {value!r}")
    return _LABEL_ALIASES[key]


# --------------------------------------------------------------------------------------------
# Generic table reader
# --------------------------------------------------------------------------------------------


def read_table(path: str | Path) -> pd.DataFrame:
    """Read CSV, TSV/TXT (official SemEval format), XLSX or JSONL into a DataFrame."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if suffix in {".txt", ".tsv"}:
        sep = "\t"
    else:
        sep = ","
    # The official SemEval-2016 files are not UTF-8 clean; fall back to latin-1.
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, sep=sep, encoding=encoding, quoting=0 if sep == "," else 3)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")


def _pick_column(frame: pd.DataFrame, *candidates: str) -> str:
    lowered = {c.lower().strip(): c for c in frame.columns}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]
    raise KeyError(f"None of the columns {candidates} found in {list(frame.columns)}")


def _clean_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return html.unescape(text).strip()


def validate_canonical(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in CANONICAL_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"Canonical table is missing columns {missing}")
    if frame["id"].duplicated().any():
        dupes = frame.loc[frame["id"].duplicated(), "id"].head().tolist()
        raise ValueError(f"Duplicate post ids, e.g. {dupes}")
    bad = set(frame["label"]) - set(LABELS)
    if bad:
        raise ValueError(f"Unknown labels {bad}")
    bad_splits = set(frame["split"]) - {"train", "val", "test"}
    if bad_splits:
        raise ValueError(f"Unknown splits {bad_splits}")
    return frame


# --------------------------------------------------------------------------------------------
# P-Stance
# --------------------------------------------------------------------------------------------


def load_pstance(
    data_dir: str | Path, targets: Optional[Iterable[str]] = None, include_val: bool = False
) -> pd.DataFrame:
    """Load the official P-Stance CSV files from ``data_dir``.

    Files are matched as ``raw_{split}_{key}.csv`` with ``key`` in ``trump, biden, bernie``.
    Post ids are ``pstance-{key}-{split}-{row}``, where ``row`` is the 0-based row index of the post
    in the official file, so they identify the post in the benchmark release. The validation split
    is skipped unless ``include_val`` is set: the paper never uses it, and skipping it avoids paying
    for glosses and embeddings that no stage reads.
    """
    data_dir = Path(data_dir)
    keys = list(targets) if targets else list(PSTANCE_TARGETS)
    splits = ("train", "val", "test") if include_val else ("train", "test")
    frames: List[pd.DataFrame] = []
    for key in keys:
        if key not in PSTANCE_TARGETS:
            raise ValueError(f"Unknown P-Stance target key '{key}' (expected {list(PSTANCE_TARGETS)})")
        for split in splits:
            path = data_dir / f"raw_{split}_{key}.csv"
            if not path.exists():
                continue
            raw = read_table(path)
            text_col = _pick_column(raw, "Tweet", "text")
            label_col = _pick_column(raw, "Stance", "label")
            frames.append(
                pd.DataFrame(
                    {
                        "id": [f"pstance-{key}-{split}-{i}" for i in range(len(raw))],
                        "dataset": "pstance",
                        "target": PSTANCE_TARGETS[key],
                        "split": split,
                        "text": raw[text_col].map(_clean_text),
                        "label": raw[label_col].map(normalise_label),
                    }
                )
            )
    if not frames:
        raise FileNotFoundError(f"No raw_{{split}}_{{target}}.csv files found in {data_dir}")
    return validate_canonical(pd.concat(frames, ignore_index=True))


# --------------------------------------------------------------------------------------------
# SemEval-2016 Task 6, Subtask A
# --------------------------------------------------------------------------------------------


def _load_semeval_file(path: str | Path, split: str) -> pd.DataFrame:
    raw = read_table(path)
    target_col = _pick_column(raw, "Target")
    text_col = _pick_column(raw, "Tweet", "text")
    label_col = _pick_column(raw, "Stance", "label")
    try:
        id_col = _pick_column(raw, "ID")
        ids = raw[id_col].map(lambda x: f"semeval2016-{int(x)}")
    except KeyError:
        # Some redistributions (e.g. StanceDataset.zip: train.csv / test.csv) have no ID column.
        ids = pd.Series([f"semeval2016-{split}-{Path(path).stem}-{i}" for i in range(len(raw))])
    return pd.DataFrame(
        {
            "id": ids,
            "dataset": "semeval2016",
            "target": raw[target_col].map(lambda x: str(x).strip()),
            "split": split,
            "text": raw[text_col].map(_clean_text),
            "label": raw[label_col].map(normalise_label),
        }
    )


def load_semeval2016(
    train_paths: Sequence[str | Path],
    test_paths: Sequence[str | Path],
    subtask_a_only: bool = True,
) -> pd.DataFrame:
    """Load SemEval-2016 Task 6 training (+ trial) and test files.

    ``subtask_a_only`` drops the Subtask B target (Donald Trump) if it appears in an input file.
    """
    frames = [_load_semeval_file(p, "train") for p in train_paths]
    frames += [_load_semeval_file(p, "test") for p in test_paths]
    frame = pd.concat(frames, ignore_index=True)
    if subtask_a_only:
        frame = frame[frame["target"].isin(SEMEVAL_SUBTASK_A_TARGETS)].reset_index(drop=True)
    return validate_canonical(frame)


# --------------------------------------------------------------------------------------------
# Optional hold-out protocol (only when no official test split is available)
# --------------------------------------------------------------------------------------------


def make_holdout_split(frame: pd.DataFrame, fraction: float = 0.1, seed: int = 0) -> pd.DataFrame:
    """Move a label-stratified ``fraction`` of each target's training posts to ``split='test'``.

    This is **not** the paper's protocol. It exists so that the pipeline can still be exercised
    when only a training split is at hand (for example, P-Stance without its official test file).
    """
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be in (0, 1)")
    frame = frame.copy()
    rng = np.random.default_rng(seed)
    train_mask = frame["split"] == "train"
    for (_, _), group in frame[train_mask].groupby(["target", "label"], sort=True):
        n_test = int(round(len(group) * fraction))
        if n_test == 0:
            continue
        chosen = rng.choice(group.index.to_numpy(), size=n_test, replace=False)
        frame.loc[chosen, "split"] = "test"
    return frame


# --------------------------------------------------------------------------------------------
# Released aspect assignments ("Clustering Results (Aspects)")
# --------------------------------------------------------------------------------------------


def load_released_aspects(root: str | Path) -> pd.DataFrame:
    """Load the released training-split aspect assignments of the paper.

    Returns a table with ``dataset, target, text, label, aspect`` (plus ``source_id`` for SemEval).
    """
    root = Path(root)
    frames: List[pd.DataFrame] = []
    for path in sorted(root.glob("PStance/*.csv")):
        raw = pd.read_csv(path)
        frames.append(
            pd.DataFrame(
                {
                    "dataset": "pstance",
                    "target": raw["Target"].astype(str).str.strip(),
                    "text": raw["Tweet"].map(_clean_text),
                    "label": raw["Stance"].map(normalise_label),
                    "aspect": raw["Aspect"].astype(int),
                    "source_id": [f"{path.stem}-{i}" for i in range(len(raw))],
                }
            )
        )
    for path in sorted(root.glob("SemEval/*.xlsx")):
        raw = pd.read_excel(path)
        frames.append(
            pd.DataFrame(
                {
                    "dataset": "semeval2016",
                    "target": raw["Target"].astype(str).str.strip(),
                    "text": raw["Tweet"].map(_clean_text),
                    "label": raw["Stance"].map(normalise_label),
                    "aspect": raw["Aspect"].astype(int),
                    "source_id": raw["ID"].map(lambda x: f"semeval2016-{int(x)}"),
                }
            )
        )
    if not frames:
        raise FileNotFoundError(f"No released aspect files found under {root}")
    return pd.concat(frames, ignore_index=True)


def summarise_splits(frame: pd.DataFrame) -> pd.DataFrame:
    """Label distribution per target and split (the layout of the paper's Table 2)."""
    table = (
        frame.groupby(["target", "split", "label"]).size().unstack("label", fill_value=0).reindex(
            columns=list(LABELS), fill_value=0
        )
    )
    table["Total"] = table.sum(axis=1)
    return table
