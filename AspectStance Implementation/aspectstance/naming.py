"""Post hoc cluster naming (Section 4.5).

Once a partition is fixed, the posts of every cluster are submitted to GPT-6 Luna with the naming
prompt of Appendix A.1. Naming only annotates the partition: it changes neither K_T nor cluster
membership, and the names never enter the classifier.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from .llm import LLMClient
from .prompts import naming_prompt


def name_clusters(
    texts: Sequence[str],
    clusters: Sequence[int],
    target: str,
    llm: LLMClient,
    max_posts: Optional[int] = None,
    seed: int = 0,
    progress: bool = True,
) -> pd.DataFrame:
    """Return ``cluster, n, share, name`` for every cluster, largest first.

    ``max_posts`` optionally caps the number of posts sent per cluster (a uniform sample); the
    paper sends every post of the cluster, which is the default.
    """
    texts = np.asarray(texts, dtype=object)
    clusters = np.asarray(clusters, dtype=np.int64)
    rng = np.random.default_rng(seed)
    ids = sorted(np.unique(clusters).tolist())
    prompts = []
    for cluster in ids:
        members = texts[clusters == cluster]
        if max_posts is not None and len(members) > max_posts:
            members = rng.choice(members, size=max_posts, replace=False)
        prompts.append(naming_prompt(members.tolist(), target))
    names = llm.complete_many(prompts, namespace="naming", desc=f"Naming {target}", progress=progress)
    sizes = np.bincount(clusters)
    table = pd.DataFrame(
        {
            "target": target,
            "cluster": ids,
            "n": [int(sizes[c]) for c in ids],
            "share": [100.0 * sizes[c] / len(clusters) for c in ids],
            "name": names,
        }
    )
    return table.sort_values("n", ascending=False).reset_index(drop=True)
