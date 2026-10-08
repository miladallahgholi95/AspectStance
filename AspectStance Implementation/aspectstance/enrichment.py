"""Target-conditioned text enrichment (Section 4.2, Eq. 4):  x~ = g(x, T).

Backends
--------
``openai``
    The paper's setting: GPT-6 Luna with the prompt of Figure 2 and medium reasoning effort.
``template``
    An offline, deterministic stand-in used only to exercise the pipeline without API access. It
    normalises the post (URLs and @mentions removed, hashtags split into words) and prefixes the
    target. It adds **no** background knowledge, so it cannot reproduce the paper's glosses or
    scores; results obtained with it must be reported as such.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from .llm import LLMClient
from .prompts import enrichment_prompt

GLOSS_BACKENDS = ("openai", "template")

_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@\w+")
_HASHTAG = re.compile(r"#(\w+)")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])")
_SPACES = re.compile(r"\s+")
_RETWEET = re.compile(r"^\s*RT\b\s*:?")


def _split_hashtag(match: "re.Match[str]") -> str:
    tag = match.group(1)
    if tag.lower() == "semst":  # SemEval-2016 collection tag carries no content
        return ""
    return _CAMEL.sub(" ", tag)


def normalise_post(text: str) -> str:
    """Remove URLs and @mentions, split hashtags into words and collapse whitespace."""
    text = _URL.sub(" ", text)
    text = _MENTION.sub(" ", text)
    text = _HASHTAG.sub(_split_hashtag, text)
    text = _RETWEET.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def template_gloss(text: str, target: str) -> str:
    """Offline stand-in for g(x, T); see the module docstring for its limits."""
    body = normalise_post(text) or "no textual content"
    return f"This tweet relates to the target {target}. It discusses: {body}"


def generate_glosses(
    texts: Sequence[str],
    targets: Sequence[str],
    backend: str = "openai",
    llm: Optional[LLMClient] = None,
    progress: bool = True,
) -> List[str]:
    """Produce one gloss per (post, target) pair."""
    if len(texts) != len(targets):
        raise ValueError("texts and targets must have the same length")
    if backend == "template":
        return [template_gloss(t, g) for t, g in zip(texts, targets)]
    if backend == "openai":
        if llm is None:
            raise ValueError("The 'openai' gloss backend needs an LLMClient")
        prompts = [enrichment_prompt(t, g) for t, g in zip(texts, targets)]
        return llm.complete_many(prompts, namespace="gloss", desc="Glosses", progress=progress)
    raise ValueError(f"Unknown gloss backend '{backend}' (expected one of {GLOSS_BACKENDS})")
