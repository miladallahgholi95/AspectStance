"""AspectStance: unsupervised discovery of target-specific aspects for stance detection.

Reference implementation of Allahgholi and Rahmani, "AspectStance: Unsupervised Discovery of
Target-Specific Aspects for Stance Detection". Heavy dependencies (UMAP, XGBoost, OpenAI) are
imported lazily, so ``import aspectstance`` is cheap.
"""

__version__ = "1.0.0"

from .config import (  # noqa: F401
    AspectStanceConfig,
    ClusteringConfig,
    EmbeddingConfig,
    ExperimentConfig,
    LLMConfig,
    RandomControlConfig,
    UMAPConfig,
)
from .model import AspectStanceModel, Prediction  # noqa: F401

__all__ = [
    "AspectStanceConfig",
    "AspectStanceModel",
    "ClusteringConfig",
    "EmbeddingConfig",
    "ExperimentConfig",
    "LLMConfig",
    "Prediction",
    "RandomControlConfig",
    "UMAPConfig",
]
