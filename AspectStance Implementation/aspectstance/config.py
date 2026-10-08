"""Hyperparameters of AspectStance.

Every default below is the setting reported in the paper (Section 5.4, "Implementation details").
Anything not listed here (K-means, KNN, XGBoost, random forest) runs at the scikit-learn / XGBoost
library defaults, exactly as in the paper.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------------------------
# Language-model and embedding settings (Sections 4.2, 4.3, 5.4)
# --------------------------------------------------------------------------------------------

#: Enrichment / naming / prompting model. API model id of OpenAI GPT-6 Luna.
DEFAULT_LLM_MODEL = "gpt-6-luna"
#: "Every GPT-6 Luna call uses the medium reasoning-effort setting".
DEFAULT_REASONING_EFFORT = "medium"
#: Encoder for both views; returns 3,072-dimensional vectors.
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"


@dataclass
class LLMConfig:
    """Settings for every call to the language model (gloss, naming, prompting baselines)."""

    model: str = DEFAULT_LLM_MODEL
    reasoning_effort: Optional[str] = DEFAULT_REASONING_EFFORT
    #: "responses" (OpenAI Responses API) or "chat" (Chat Completions API).
    api: str = "responses"
    #: Number of concurrent requests.
    workers: int = 8
    #: Retries handled by the OpenAI SDK (exponential back-off).
    max_retries: int = 8


@dataclass
class EmbeddingConfig:
    """Settings for the text encoder E(.) of Eq. (5)."""

    #: "openai" (paper), "wordllama" (offline, pretrained) or "lsa" (offline, TF-IDF + SVD).
    backend: str = "openai"
    model: str = DEFAULT_EMBEDDING_MODEL
    batch_size: int = 256


# --------------------------------------------------------------------------------------------
# Geometric stage (Sections 4.3 and 4.4)
# --------------------------------------------------------------------------------------------


@dataclass
class UMAPConfig:
    """UMAP settings: n_components and metric depart from the library defaults (Section 5.4)."""

    n_components: int = 20
    n_neighbors: int = 15
    min_dist: float = 0.1
    metric: str = "cosine"


@dataclass
class ClusteringConfig:
    """Silhouette sweep over the candidate inventory sizes K = 2..30 (Section 4.4)."""

    k_min: int = 2
    k_max: int = 30
    silhouette_metric: str = "cosine"


@dataclass
class RandomControlConfig:
    """Clustering-strategy control (Section 5.3): K = 5..20, ten random assignments per K."""

    k_min: int = 5
    k_max: int = 20
    draws_per_k: int = 10

    @property
    def n_configurations(self) -> int:
        return (self.k_max - self.k_min + 1) * self.draws_per_k


# --------------------------------------------------------------------------------------------
# Experiment protocol (Sections 5.3 and 5.4)
# --------------------------------------------------------------------------------------------


@dataclass
class ExperimentConfig:
    """Everything the ten-seed evaluation needs."""

    #: "Every score reported for AspectStance and the Base Method is the mean of ten runs that
    #: differ only in the random seed."
    seeds: List[int] = field(default_factory=lambda: list(range(10)))
    umap: UMAPConfig = field(default_factory=UMAPConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    random_control: RandomControlConfig = field(default_factory=RandomControlConfig)
    run_base: bool = True
    run_random_control: bool = True
    run_invariance_checks: bool = True
    #: Parallel (target, seed) jobs. Results do not depend on this value.
    n_jobs: int = 1
    #: Optional subset of targets to run (default: every target in the dataset).
    targets: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


# --------------------------------------------------------------------------------------------
# YAML loading
# --------------------------------------------------------------------------------------------


def _update_dataclass(obj: Any, values: Dict[str, Any]) -> Any:
    """Recursively overwrite the fields of a dataclass instance from a mapping."""
    known = {f.name: f for f in dataclasses.fields(obj)}
    for key, value in values.items():
        if key not in known:
            raise KeyError(f"Unknown configuration key '{key}' for {type(obj).__name__}")
        current = getattr(obj, key)
        if dataclasses.is_dataclass(current) and isinstance(value, dict):
            _update_dataclass(current, value)
        else:
            setattr(obj, key, value)
    return obj


@dataclass
class AspectStanceConfig:
    """Top-level configuration, loadable from ``configs/paper.yaml``."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AspectStanceConfig":
        import yaml

        with open(path, "r", encoding="utf-8") as handle:
            values = yaml.safe_load(handle) or {}
        return _update_dataclass(cls(), values)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def parse_seeds(spec: str) -> List[int]:
    """Parse ``"0-9"``, ``"0,3,7"`` or ``"0-4,10"`` into a sorted list of unique seeds."""
    seeds: List[int] = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            seeds.extend(range(int(start), int(end) + 1))
        else:
            seeds.append(int(part))
    if not seeds:
        raise ValueError(f"No seeds in '{spec}'")
    return sorted(set(seeds))
