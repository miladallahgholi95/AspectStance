"""Check the released training-split aspect assignments against the paper's inventory tables.

The repository folder ``Clustering Results (Aspects)`` holds, for every training post, the aspect
cluster it was assigned to in the run shown in Tables 5 and 6 of the paper. This module recomputes
the cluster sizes and shares from those files, compares them with the published tables, attaches
the published aspect names wherever a size identifies a cluster unambiguously, and reports how the
stance labels are distributed inside each cluster.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List

import pandas as pd

from .data import LABELS, display_name, load_released_aspects

#: Tables 5 and 6 of the paper: K, cosine silhouette and (size, generated name), largest first.
PAPER_INVENTORIES: Dict[str, Dict] = {
    "Donald Trump": {"dataset": "pstance", "k": 16, "silhouette": 0.91, "clusters": [
        (1160, "Direct messages to Trump / POTUS (addressing him directly)"),
        (936, "Sparse-content and cross-cutting mentions"),
        (850, "Elections, voting, and campaign dynamics"),
        (732, "Partisan conflict and congressional politics (Dems vs GOP)"),
        (470, "Investigations, corruption, and legal scandals"),
        (399, "Impeachment and accountability (impeachment, resign, jail, 25th)"),
        (310, "COVID-19 / coronavirus response and public health debate"),
        (267, "Pro-Trump praise, MAGA slogans, and rally enthusiasm"),
        (249, "Media, \"fake news\", and conflicts with platforms"),
        (231, "Anti-Trump character attacks, ridicule, and insults"),
        (197, "Economy, jobs, markets, taxes, and trade"),
        (139, "Immigration, border, asylum, and the wall"),
        (139, "Foreign policy and national security"),
        (112, "Democracy, constitution, rule-of-law, and authoritarianism framing"),
        (111, "Race, policing, protests, and civil unrest"),
        (60, "Conspiracy, QAnon, and \"deep state\" narratives"),
    ]},
    "Joe Biden": {"dataset": "pstance", "k": 12, "silhouette": 0.89, "clusters": [
        (1175, "Broad political commentary and cross-cutting mentions"),
        (1051, "Scandals, allegations, and controversy narratives"),
        (723, "Obama-era/VP legacy and major Democratic relationships"),
        (588, "Campaign updates (events, appearances, media coverage)"),
        (447, "Debates and comparisons with other Democratic candidates"),
        (377, "Policy positions and issue proposals"),
        (329, "General praise/support for Biden's leadership and character"),
        (286, "General criticism/attacks on Biden (non-scandal)"),
        (283, "Election results, polls, primaries, and delegate math"),
        (258, "Fundraising, volunteering, and voter mobilization"),
        (189, "Trump matchup and anti-Trump / anti-GOP framing"),
        (100, "Personal anecdotes, humor, and pop-culture side chatter"),
    ]},
    "Bernie Sanders": {"dataset": "pstance", "k": 9, "silhouette": 0.93, "clusters": [
        (995, "Polls, primaries, elections, and campaign developments"),
        (975, "Neutral commentary, links, quotes, and miscellaneous mentions"),
        (845, "DNC/establishment and media-bias or \"rigging\" narratives"),
        (777, "Comparisons with other Democrats and debate-focused discussion"),
        (472, "Policy and issue advocacy"),
        (472, "Anti-Bernie criticism and attacks"),
        (256, "Pro-Bernie support, movement slogans, and encouragement"),
        (210, "Fundraising, donations, and volunteer organizing"),
        (54, "GOP/Republican contrast and partisan framing"),
    ]},
    "Atheism": {"dataset": "semeval2016", "k": 5, "silhouette": 0.94, "clusters": [
        (198, "Debates, skepticism, humor, and miscellaneous commentary"),
        (135, "Faith-based encouragement and spiritual reflections"),
        (75, "Prayer, worship, and devotional praise"),
        (59, "Scripture citations and verse quotations"),
        (46, "Religion in social/political debates (equality, law, public life)"),
    ]},
    "Climate Change is a Real Concern": {"dataset": "semeval2016", "k": 5, "silhouette": 0.87, "clusters": [
        (233, "Broad climate-change discussion and cross-cutting themes"),
        (54, "Everyday weather anecdotes and seasonal oddities"),
        (44, "Politics, policy, and politicized arguments (incl. denial/hoax claims)"),
        (34, "Personal action, awareness, and solutions (sustainability + energy)"),
        (30, "Scientific evidence, measurements, and physical impacts"),
    ]},
    "Feminist Movement": {"dataset": "semeval2016", "k": 5, "silhouette": 0.85, "clusters": [
        (496, "General discussions of feminism, gender roles, and equality debates"),
        (61, "Gamergate and online gaming culture disputes"),
        (38, "Sexism, misogyny, harassment, and violence against women"),
        (37, "Pro-feminism advocacy, empowerment, and equality messaging"),
        (32, "Backlash, anti-feminism, and men's-rights framing"),
    ]},
    "Hillary Clinton": {"dataset": "semeval2016", "k": 6, "silhouette": 0.89, "clusters": [
        (387, "General mentions and miscellaneous commentary"),
        (73, "Email/Benghazi/ethics scandals and corruption narratives"),
        (71, "Campaign, elections, polling, and voting talk"),
        (57, "Comparisons with other politicians and party politics"),
        (52, "Support, admiration, and pro-Hillary enthusiasm"),
        (49, "Hostile attacks, memes, and criminality claims (\"lock her up\")"),
    ]},
    "Legalization of Abortion": {"dataset": "semeval2016", "k": 5, "silhouette": 0.92, "clusters": [
        (422, "Pro-life moral framing and general abortion debates"),
        (81, "Courts, laws, and legislation (SCOTUS, Roe v. Wade, bills)"),
        (56, "Healthcare context: clinics, contraception, and exception cases"),
        (49, "Religion-based arguments and prayerful appeals"),
        (45, "Pro-choice autonomy and women's rights framing"),
    ]},
}


def _names_by_size(clusters) -> Dict[int, List[str]]:
    names: Dict[int, List[str]] = {}
    for size, name in clusters:
        names.setdefault(size, []).append(name)
    return names


def inventory_table(frame: pd.DataFrame, target: str) -> pd.DataFrame:
    """Per-cluster size, share, stance counts, purity and the size-matched paper name."""
    rows = frame[frame["target"] == target]
    paper = PAPER_INVENTORIES.get(target)
    names = _names_by_size(paper["clusters"]) if paper else {}
    labels = [label for label in LABELS if (rows["label"] == label).any()]
    table = []
    for aspect, group in rows.groupby("aspect"):
        counts = Counter(group["label"])
        n = len(group)
        candidates = names.get(n, [])
        if len(candidates) == 1:
            name = candidates[0]
        elif len(candidates) > 1:
            name = " / ".join(candidates) + " (same size: ambiguous)"
        else:
            name = ""
        table.append(
            {
                "aspect_id": int(aspect),
                "n": n,
                "share": 100.0 * n / len(rows),
                **{label: counts.get(label, 0) for label in labels},
                "majority_stance": max(labels, key=lambda lab: counts.get(lab, 0)),
                "purity": 100.0 * max(counts.values()) / n,
                "paper_name": name,
            }
        )
    return pd.DataFrame(table).sort_values("n", ascending=False).reset_index(drop=True)


def check_released_inventories(root: str | Path) -> str:
    """Markdown report comparing the released assignment files with Tables 5 and 6."""
    frame = load_released_aspects(root)
    lines = [
        "# Released aspect inventories vs. the paper",
        "",
        "Recomputed from the files in `Clustering Results (Aspects)/` (training splits only).",
        "*Stance purity* is the share of a cluster's posts that carry its majority stance label;",
        "*cluster-majority accuracy* labels every training post with its cluster's majority stance.",
        "",
        "| Dataset | Target | Posts | K | K (paper) | Sizes = paper | Majority-class acc. | Cluster-majority acc. |",
        "|---|---|---:|---:|---:|:---:|---:|---:|",
    ]
    details = []
    for target in PAPER_INVENTORIES:
        rows = frame[frame["target"] == target]
        if rows.empty:
            continue
        paper = PAPER_INVENTORIES[target]
        table = inventory_table(frame, target)
        released_sizes = sorted(table["n"].tolist(), reverse=True)
        paper_sizes = [size for size, _ in paper["clusters"]]
        match = released_sizes == paper_sizes
        majority_acc = 100.0 * rows["label"].value_counts().max() / len(rows)
        cluster_acc = 100.0 * float(
            sum(group["label"].value_counts().max() for _, group in rows.groupby("aspect"))
        ) / len(rows)
        lines.append(
            f"| {paper['dataset']} | {display_name(target)} | {len(rows):,} | {len(table)} | {paper['k']} | "
            f"{'yes' if match else 'no'} | {majority_acc:.1f}% | {cluster_acc:.1f}% |"
        )
        detail = [f"### {display_name(target)}  (K = {len(table)}, paper silhouette {paper['silhouette']:.2f})", ""]
        if not match:
            diff = sum(paper_sizes) - sum(released_sizes)
            detail.append(
                f"> Cluster sizes differ from the paper: the released file has {len(rows)} posts, the "
                f"paper's table {sum(paper_sizes)} (difference {diff}). This is consistent with the "
                "SemEval-2016 trial posts (IDs 1-100: 50 Hillary Clinton, 50 Legalization of Abortion), "
                "which the paper adds to the training split, being absent from the released file. "
                "Names are attached only where a size matches exactly."
            )
            detail.append("")
        stance_cols = [c for c in LABELS if c in table.columns]
        header = "| Id | n | Share | " + " | ".join(stance_cols) + " | Purity | Paper name (matched by size) |"
        detail += [header, "|" + "---:|" * (4 + len(stance_cols)) + "---|"]
        for _, r in table.iterrows():
            detail.append(
                f"| {r['aspect_id']} | {r['n']} | {r['share']:.1f}% | "
                + " | ".join(str(r[c]) for c in stance_cols)
                + f" | {r['purity']:.0f}% | {r['paper_name']} |"
            )
        details += detail + [""]
    lines += ["", "## Per-target inventories", ""] + details
    return "\n".join(lines)
