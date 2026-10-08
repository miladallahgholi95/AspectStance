"""On-disk layout shared by the CLI stages.

::

    <workspace>/
        dataset.csv                  canonical table: id, dataset, target, split, text, label
        glosses.csv                  id, gloss, gloss_backend, gloss_model
        embeddings/<backend>/        post.npy, gloss.npy, meta.json (row-aligned with dataset.csv)
        cache.sqlite                 every LLM response and API embedding, keyed by content hash
        results/<name>/              experiment artefacts (metrics, predictions, assignments, summary)
        models/<target>/seed<k>.joblib

``dataset.csv`` and ``glosses.csv`` contain tweet texts: keep workspaces out of version control
(the repository's ``.gitignore`` already does so for ``workspace*/``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .cache import KVCache
from .data import validate_canonical


def _ids_digest(ids) -> str:
    return hashlib.sha256("\n".join(map(str, ids)).encode("utf-8")).hexdigest()


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- paths -----------------------------------------------------------------------------------
    @property
    def dataset_path(self) -> Path:
        return self.root / "dataset.csv"

    @property
    def glosses_path(self) -> Path:
        return self.root / "glosses.csv"

    def embeddings_dir(self, backend: str) -> Path:
        return self.root / "embeddings" / backend

    def results_dir(self, name: str) -> Path:
        return self.root / "results" / name

    def model_path(self, target_slug: str, seed: int) -> Path:
        return self.root / "models" / target_slug / f"seed{seed}.joblib"

    def cache(self) -> KVCache:
        return KVCache(self.root / "cache.sqlite")

    # -- dataset -----------------------------------------------------------------------------------
    def save_dataset(self, frame: pd.DataFrame) -> None:
        validate_canonical(frame).to_csv(self.dataset_path, index=False)

    def load_dataset(self) -> pd.DataFrame:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"{self.dataset_path} not found: run `aspectstance prepare` first")
        frame = pd.read_csv(self.dataset_path, dtype={"id": str}, keep_default_na=False)
        return validate_canonical(frame)

    # -- glosses ---------------------------------------------------------------------------------------
    def save_glosses(self, ids, glosses, backend: str, model: str) -> None:
        pd.DataFrame(
            {"id": list(ids), "gloss": list(glosses), "gloss_backend": backend, "gloss_model": model}
        ).to_csv(self.glosses_path, index=False)

    def load_glosses(self, frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if not self.glosses_path.exists():
            raise FileNotFoundError(f"{self.glosses_path} not found: run `aspectstance enrich` first")
        glosses = pd.read_csv(self.glosses_path, dtype={"id": str}, keep_default_na=False)
        if frame is not None and glosses["id"].tolist() != frame["id"].tolist():
            raise ValueError("glosses.csv is not row-aligned with dataset.csv; re-run `enrich`")
        return glosses

    # -- embeddings ------------------------------------------------------------------------------------
    def save_embeddings(
        self, backend: str, ids, post: np.ndarray, gloss: np.ndarray, meta: Dict[str, Any]
    ) -> None:
        directory = self.embeddings_dir(backend)
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "post.npy", np.asarray(post, dtype=np.float32))
        np.save(directory / "gloss.npy", np.asarray(gloss, dtype=np.float32))
        meta = dict(meta, n=len(ids), dim=int(post.shape[1]), ids_sha256=_ids_digest(ids))
        (directory / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def available_embeddings(self) -> list:
        root = self.root / "embeddings"
        return sorted(p.name for p in root.iterdir() if (p / "post.npy").exists()) if root.exists() else []

    def load_embeddings(self, backend: str, ids) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        directory = self.embeddings_dir(backend)
        if not (directory / "post.npy").exists():
            raise FileNotFoundError(f"No '{backend}' embeddings in {directory}: run `aspectstance embed`")
        meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
        if meta.get("ids_sha256") != _ids_digest(ids):
            raise ValueError(f"Embeddings in {directory} are not row-aligned with dataset.csv; re-run `embed`")
        return np.load(directory / "post.npy"), np.load(directory / "gloss.npy"), meta
