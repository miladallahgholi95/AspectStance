"""Text encoders E(.) for the post and gloss views (Section 4.3, Eq. 5).

Backends
--------
``openai``
    The paper's setting: OpenAI ``text-embedding-3-large`` (3,072 dimensions), cached on disk.
``wordllama``
    Offline, pretrained 256-dimensional WordLlama embeddings (``pip install wordllama``). The
    weights ship inside the PyPI wheel, so no download is needed at run time.
``lsa``
    Offline, dependency-free TF-IDF + truncated SVD (latent semantic analysis). It has to be fitted;
    the CLI fits it on the training split only.

Only ``openai`` corresponds to the paper. The offline encoders exist so that the full pipeline can
be run and tested without network access; their scores are not comparable with the paper's.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, List, Optional, Sequence

import numpy as np

from .cache import KVCache, make_key

logger = logging.getLogger(__name__)

EMBEDDING_BACKENDS = ("openai", "wordllama", "lsa")


def _as_matrix(vectors: Sequence[np.ndarray]) -> np.ndarray:
    return np.vstack([np.asarray(v, dtype=np.float32) for v in vectors]).astype(np.float32)


class OpenAIEmbedder:
    """``text-embedding-3-large`` embeddings, batched and cached per text."""

    name = "openai"

    def __init__(
        self,
        model: str = "text-embedding-3-large",
        batch_size: int = 256,
        cache: Optional[KVCache] = None,
        client: Any = None,
        max_retries: int = 8,
    ):
        self.model = model
        self.batch_size = batch_size
        self.cache = cache
        if client is None:
            from openai import OpenAI

            client = OpenAI(max_retries=max_retries)
        self.client = client

    def _key(self, text: str) -> str:
        return make_key("embedding", self.model, text)

    def embed(self, texts: Sequence[str], progress: bool = True) -> np.ndarray:
        # The API rejects empty strings.
        texts = [t if t.strip() else " " for t in texts]
        vectors: List[Optional[np.ndarray]] = [None] * len(texts)
        keys = [self._key(t) for t in texts]
        if self.cache is not None:
            found = self.cache.get_many(keys)
            for i, key in enumerate(keys):
                if key in found:
                    vectors[i] = KVCache.decode_vector(found[key])
        # Embed each distinct missing text once.
        missing = list(dict.fromkeys(texts[i] for i, v in enumerate(vectors) if v is None))
        computed = {}
        batches = [missing[s : s + self.batch_size] for s in range(0, len(missing), self.batch_size)]
        iterator = batches
        if progress and batches:
            from tqdm.auto import tqdm

            iterator = tqdm(batches, desc=f"Embeddings ({self.model})")
        for batch in iterator:
            response = self.client.embeddings.create(model=self.model, input=list(batch))
            data = sorted(response.data, key=lambda item: item.index)
            if len(data) != len(batch):
                raise RuntimeError("Embedding API returned a different number of vectors")
            rows = []
            for text, item in zip(batch, data):
                vector = np.asarray(item.embedding, dtype=np.float32)
                computed[text] = vector
                rows.append((self._key(text), KVCache.encode_vector(vector)))
            if self.cache is not None:
                self.cache.set_many(rows)
        for i, vector in enumerate(vectors):
            if vector is None:
                vectors[i] = computed[texts[i]]
        return _as_matrix(vectors)  # type: ignore[arg-type]


class WordLlamaEmbedder:
    """Offline WordLlama embeddings (L2-normalised)."""

    name = "wordllama"

    def __init__(self, dim: int = 256, cache_dir: Optional[str | Path] = None):
        try:
            import wordllama
            from wordllama import WordLlama
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise ImportError("The 'wordllama' backend needs `pip install wordllama`") from error
        package_dir = Path(wordllama.__file__).parent
        cache_dir = Path(cache_dir or Path.home() / ".cache" / "aspectstance" / "wordllama")
        # WordLlama bundles its tokenizer in the wheel but looks for it in its cache directory;
        # copying it there makes loading work without network access.
        bundled = package_dir / "tokenizers" / "l2_supercat_tokenizer_config.json"
        target = cache_dir / "tokenizers" / bundled.name
        if bundled.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(bundled, target)
        self.model = WordLlama.load(dim=dim, cache_dir=cache_dir.resolve(), disable_download=False)
        self.dim = dim

    def embed(self, texts: Sequence[str], progress: bool = True) -> np.ndarray:
        return np.asarray(self.model.embed(list(texts), norm=True), dtype=np.float32)


class LSAEmbedder:
    """TF-IDF (word 1-2 grams) followed by truncated SVD; must be fitted before use."""

    name = "lsa"

    def __init__(self, n_components: int = 300, random_state: int = 0):
        self.n_components = n_components
        self.random_state = random_state
        self.vectoriser_ = None
        self.svd_ = None

    def fit(self, texts: Sequence[str]) -> "LSAEmbedder":
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        texts = list(texts)
        self.vectoriser_ = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2).fit(texts)
        matrix = self.vectoriser_.transform(texts)
        n_components = max(1, min(self.n_components, matrix.shape[1] - 1, matrix.shape[0] - 1))
        self.svd_ = TruncatedSVD(n_components=n_components, random_state=self.random_state).fit(matrix)
        return self

    def embed(self, texts: Sequence[str], progress: bool = True) -> np.ndarray:
        if self.vectoriser_ is None or self.svd_ is None:
            raise RuntimeError("LSAEmbedder must be fitted first")
        matrix = self.svd_.transform(self.vectoriser_.transform(list(texts))).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.maximum(norms, 1e-12)


def build_embedder(
    backend: str,
    model: str = "text-embedding-3-large",
    batch_size: int = 256,
    cache: Optional[KVCache] = None,
    client: Any = None,
):
    if backend == "openai":
        return OpenAIEmbedder(model=model, batch_size=batch_size, cache=cache, client=client)
    if backend == "wordllama":
        return WordLlamaEmbedder()
    if backend == "lsa":
        return LSAEmbedder()
    raise ValueError(f"Unknown embedding backend '{backend}' (expected one of {EMBEDDING_BACKENDS})")
