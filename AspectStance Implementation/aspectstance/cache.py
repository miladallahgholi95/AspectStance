"""A small SQLite key-value cache for language-model responses and embeddings.

Generating glosses and embeddings is the only expensive, paid and non-deterministic part of the
pipeline, so every response is written to disk as soon as it arrives. Interrupted runs resume where
they stopped, and the paper's protocol of generating the glosses and embeddings *once* and reusing
them across all ten seeds falls out naturally.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

import numpy as np


def make_key(*parts: object) -> str:
    """Stable SHA-256 key for an arbitrary tuple of JSON-serialisable parts."""
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class KVCache:
    """Thread-safe persistent ``key -> bytes`` store."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value BLOB NOT NULL)")
        self._conn.commit()

    # -- raw bytes ---------------------------------------------------------------------------
    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            row = self._conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return None if row is None else bytes(row[0])

    def get_many(self, keys: Sequence[str]) -> Dict[str, bytes]:
        found: Dict[str, bytes] = {}
        unique = list(dict.fromkeys(keys))
        with self._lock:
            for start in range(0, len(unique), 900):  # SQLite parameter limit
                chunk = unique[start : start + 900]
                marks = ",".join("?" * len(chunk))
                for key, value in self._conn.execute(
                    f"SELECT key, value FROM kv WHERE key IN ({marks})", chunk
                ):
                    found[key] = bytes(value)
        return found

    def set(self, key: str, value: bytes) -> None:
        self.set_many([(key, value)])

    def set_many(self, items: Iterable[Tuple[str, bytes]]) -> None:
        rows = [(k, sqlite3.Binary(v)) for k, v in items]
        if not rows:
            return
        with self._lock:
            self._conn.executemany("INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", rows)
            self._conn.commit()

    def __len__(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM kv").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- typed helpers -------------------------------------------------------------------------
    def get_text(self, key: str) -> Optional[str]:
        value = self.get(key)
        return None if value is None else value.decode("utf-8")

    def set_text(self, key: str, text: str) -> None:
        self.set(key, text.encode("utf-8"))

    @staticmethod
    def encode_vector(vector: np.ndarray) -> bytes:
        return np.asarray(vector, dtype=np.float32).tobytes()

    @staticmethod
    def decode_vector(value: bytes) -> np.ndarray:
        return np.frombuffer(value, dtype=np.float32).copy()
