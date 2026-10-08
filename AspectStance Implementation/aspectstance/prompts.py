"""The four GPT-6 Luna prompts, reproduced verbatim from the paper (Figure 2 and Appendix A).

Braced fields are substituted at call time with :func:`render`, which performs a single pass so
that braces inside a tweet are never interpreted as fields.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional, Sequence, Tuple

#: Figure 2 -- enrichment prompt, issued once per post to produce the gloss  x~ = g(x, T).
ENRICHMENT_PROMPT = (
    "Task: Explain how the tweet relates to the target. Identify the specific event, controversy, "
    "or aspect of the target it refers to. Briefly summarize that event or aspect and describe its "
    "connection to the tweet in 30-50 words. Do not quote the tweet; focus on interpretation and "
    "explanation.\n"
    "\n"
    'Tweet: "{tweet}"\n'
    'Target: "{target}"'
)

#: Appendix A.1 -- post hoc cluster naming, issued once per induced cluster.
NAMING_PROMPT = (
    "Task: Given a cluster of tweets associated with a target, identify and summarize the main topic "
    "or topics discussed in the cluster in relation to that target. Describe the dominant themes and "
    "the specific aspects of the target they refer to. If multiple distinct themes are present, "
    "report the main ones. If no coherent dominant theme exists and the tweets are highly diverse, "
    "explicitly label the cluster as semantically dispersed. Base the analysis on recurring semantic "
    "patterns across the tweets, not isolated examples. Keep the response concise and descriptive.\n"
    "\n"
    'Tweets: "{tweets}"\n'
    'Target: "{target}"'
)

_LABEL_DEFINITIONS = {
    "FAVOR": "FAVOR: The tweet expresses support or a positive stance toward the target.",
    "AGAINST": "AGAINST: The tweet expresses opposition or a negative stance toward the target.",
    "NONE": "NONE: The tweet expresses no clear stance toward the target.",
}

_STANCE_HEADER = (
    "Task: Determine the stance expressed in the tweet toward the given target. Classify the tweet "
    "into exactly one of the following labels:"
)


def _label_block(labels: Sequence[str]) -> str:
    return "\n".join(_LABEL_DEFINITIONS[label] for label in labels)


def _return_line(labels: Sequence[str]) -> str:
    if len(labels) == 2:
        options = f"{labels[0]} or {labels[1]}"
    else:
        options = ", ".join(labels[:-1]) + f", or {labels[-1]}"
    return f"Return only one label: {options}."


def zero_shot_prompt(labels: Sequence[str] = ("FAVOR", "AGAINST", "NONE")) -> str:
    """Appendix A.2. For P-Stance the label set is restricted to FAVOR and AGAINST."""
    return (
        f"{_STANCE_HEADER}\n"
        "\n"
        f"{_label_block(labels)}\n"
        "\n"
        'Tweet: "{tweet}"\n'
        'Target: "{target}"\n'
        "\n"
        f"{_return_line(labels)}"
    )


def few_shot_prompt(labels: Sequence[str] = ("FAVOR", "AGAINST", "NONE")) -> str:
    """Appendix A.3 -- retrieval-augmented few-shot prompt."""
    return (
        f"{_STANCE_HEADER}\n"
        "\n"
        f"{_label_block(labels)}\n"
        "\n"
        "Use the following labeled examples as guidance:\n"
        "\n"
        "Few-shot Examples:\n"
        '"{examples}"\n'
        "\n"
        'Tweet: "{tweet}"\n'
        'Target: "{target}"\n'
        "\n"
        f"{_return_line(labels)}"
    )


_FIELD = re.compile(r"\{(tweet|target|tweets|examples)\}")


def render(template: str, **fields: str) -> str:
    """Substitute ``{tweet}``, ``{target}``, ``{tweets}`` and ``{examples}`` in one pass."""

    def substitute(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in fields:
            raise KeyError(f"Missing prompt field '{name}'")
        return str(fields[name])

    return _FIELD.sub(substitute, template)


def enrichment_prompt(tweet: str, target: str) -> str:
    return render(ENRICHMENT_PROMPT, tweet=tweet, target=target)


def naming_prompt(tweets: Iterable[str], target: str) -> str:
    joined = "\n".join(f"- {t}" for t in tweets)
    return render(NAMING_PROMPT, tweets=joined, target=target)


def format_examples(examples: Iterable[Tuple[str, str, str]]) -> str:
    """Format ``(tweet, target, label)`` triples for the few-shot prompt, one per line."""
    return "\n".join(f'Tweet: "{t}" | Target: "{g}" | Label: {y}' for t, g, y in examples)


_LABEL_PATTERN = re.compile(r"\b(FAVOR|FAVOUR|AGAINST|NONE)\b")


def parse_label(response: Optional[str], labels: Sequence[str]) -> Optional[str]:
    """Return the first allowed label in a model response, or ``None`` when there is none."""
    if not response:
        return None
    for match in _LABEL_PATTERN.finditer(response.upper()):
        label = "FAVOR" if match.group(1) == "FAVOUR" else match.group(1)
        if label in labels:
            return label
    return None
