"""Aggregate the per-seed artefacts into the paper's tables (Tables 3-5 and Section 6.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .data import display_name

ASPECTSTANCE = "AspectStance"
BASE = "Base"


def _read(path: Path) -> Optional[pd.DataFrame]:
    return pd.read_csv(path) if path.exists() else None


def _fmt(value: Optional[float], digits: int = 1, sign: bool = False) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "--"
    return f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"


def summarise(results_dir: str | Path) -> Dict[str, Any]:
    """Build a JSON-serialisable summary from the CSV files written by ``run_experiments``."""
    results_dir = Path(results_dir)
    metrics = pd.read_csv(results_dir / "metrics_per_seed.csv")
    inventory = _read(results_dir / "inventory.csv")
    random_runs = _read(results_dir / "random_control_runs.csv")
    invariance = _read(results_dir / "invariance.csv")
    pooled = _read(results_dir / "pooled_f_micro_per_seed.csv")
    runs = _read(results_dir / "runs.csv")

    targets: List[str] = list(dict.fromkeys(metrics["target"]))
    seeds = sorted(metrics["seed"].unique().tolist())
    has_base = (metrics["method"] == BASE).any()

    per_target = []
    for target in targets:
        rows = metrics[metrics["target"] == target]
        asp = rows.loc[rows["method"] == ASPECTSTANCE, "f1_avg"]
        entry: Dict[str, Any] = {
            "target": target,
            "display_name": display_name(target),
            "aspectstance_mean": float(asp.mean()),
            "aspectstance_std": float(asp.std(ddof=1)) if len(asp) > 1 else 0.0,
            "aspectstance_f1_favor": float(rows.loc[rows["method"] == ASPECTSTANCE, "f1_favor"].mean()),
            "aspectstance_f1_against": float(rows.loc[rows["method"] == ASPECTSTANCE, "f1_against"].mean()),
        }
        if has_base:
            base = rows.loc[rows["method"] == BASE, "f1_avg"]
            by_seed = rows.pivot_table(index="seed", columns="method", values="f1_avg")
            entry.update(
                base_mean=float(base.mean()),
                base_std=float(base.std(ddof=1)) if len(base) > 1 else 0.0,
                delta=float(asp.mean() - base.mean()),
                seeds_with_positive_gain=int((by_seed[ASPECTSTANCE] > by_seed[BASE]).sum()),
            )
        if inventory is not None:
            inv = inventory[inventory["target"] == target].drop_duplicates("seed")
            ks = inv["k"].astype(int).tolist()
            values, counts = np.unique(ks, return_counts=True)
            largest = (
                inventory[inventory["target"] == target].groupby("seed")["share_train"].max().mean()
            )
            entry.update(
                k_per_seed=ks,
                k_mode=int(values[counts.argmax()]),
                k_stable=bool(len(values) == 1),
                silhouette_mean=float(inv["silhouette"].mean()),
                silhouette_std=float(inv["silhouette"].std(ddof=1)) if len(inv) > 1 else 0.0,
                largest_cluster_share=float(largest),
            )
        if random_runs is not None and (random_runs["target"] == target).any():
            rr = random_runs.loc[random_runs["target"] == target, "f1_avg"]
            entry.update(
                random_best=float(rr.max()),
                random_mean=float(rr.mean()),
                random_median=float(rr.median()),
                random_n=int(len(rr)),
            )
        if invariance is not None and (invariance["target"] == target).any():
            inv_rows = invariance[invariance["target"] == target]
            for method, key in (
                ("AspectStance (relabelled clusters)", "relabelled"),
                ("AspectStance (permuted one-hot columns)", "permuted"),
            ):
                sel = inv_rows[inv_rows["method"] == method]
                entry[f"{key}_mean"] = float(sel["f1_avg"].mean())
                entry[f"{key}_agreement"] = float(sel["agreement_with_aspectstance"].mean())
        per_target.append(entry)

    # Equal-target average (F-macro_T) per seed, then its mean and spread over seeds.
    def macro_per_seed(method: str) -> pd.Series:
        sel = metrics[metrics["method"] == method]
        return sel.groupby("seed")["f1_avg"].mean()

    asp_macro = macro_per_seed(ASPECTSTANCE)
    average: Dict[str, Any] = {
        "aspectstance": float(np.mean([e["aspectstance_mean"] for e in per_target])),
        "aspectstance_std_over_seeds": float(asp_macro.std(ddof=1)) if len(asp_macro) > 1 else 0.0,
    }
    if has_base:
        base_macro = macro_per_seed(BASE)
        average.update(
            base=float(np.mean([e["base_mean"] for e in per_target])),
            base_std_over_seeds=float(base_macro.std(ddof=1)) if len(base_macro) > 1 else 0.0,
        )
        average["delta"] = average["aspectstance"] - average["base"]
        average["targets_with_positive_mean_gain"] = int(sum(e["delta"] > 0 for e in per_target))
    if all("random_best" in e for e in per_target):
        average["random_best"] = float(np.mean([e["random_best"] for e in per_target]))
        average["random_mean"] = float(np.mean([e["random_mean"] for e in per_target]))
        average["random_n_per_target"] = int(min(e["random_n"] for e in per_target))
    if all("relabelled_mean" in e for e in per_target):
        average["relabelled"] = float(np.mean([e["relabelled_mean"] for e in per_target]))
        average["permuted"] = float(np.mean([e["permuted_mean"] for e in per_target]))

    summary: Dict[str, Any] = {
        "metric": "F1_avg = (F1_FAVOR + F1_AGAINST) / 2, averaged over targets (F-macro_T), 0-100",
        "seeds": seeds,
        "targets": targets,
        "per_target": per_target,
        "target_average": average,
    }
    if pooled is not None:
        summary["pooled_f_micro"] = {
            col: float(pooled[col].mean()) for col in pooled.columns if col != "seed"
        }
    if runs is not None:
        summary["min_train_routing_agreement"] = float(runs["train_routing_agreement"].min())
        summary["total_compute_seconds"] = float(runs["seconds"].sum())
    config_path = results_dir / "run_config.json"
    if config_path.exists():
        summary["run"] = json.loads(config_path.read_text(encoding="utf-8"))
    return summary


def to_markdown(summary: Dict[str, Any], title: str = "AspectStance results") -> str:
    """Render the summary in the layout of the paper's tables."""
    per_target = sorted(summary["per_target"], key=lambda e: -e["aspectstance_mean"])
    avg = summary["target_average"]
    has_base = "base" in avg
    seeds = summary["seeds"]
    lines = [f"# {title}", ""]
    run = summary.get("run", {})
    backend = run.get("backends")
    lines.append(
        f"Seeds: {len(seeds)} ({seeds[0]}-{seeds[-1]}) · Targets: {len(per_target)} · "
        "Metric: F1_avg (mean of FAVOR and AGAINST F1), equal-weight target average (F-macro_T)."
    )
    if backend:
        lines.append("")
        lines.append(
            "Backends: " + ", ".join(f"{k} = `{v}`" for k, v in backend.items())
        )
    if run.get("protocol"):
        lines.append("")
        lines.append(f"Evaluation protocol: {run['protocol']}")
    lines += ["", "## Per-target F1_avg (layout of Table 3)", ""]
    header = "| Target | AspectStance | Base | Δ | Seeds with gain |" if has_base else "| Target | AspectStance |"
    lines.append(header)
    lines.append("|---|---:|---:|---:|---:|" if has_base else "|---|---:|")
    for e in per_target:
        cell = f"{_fmt(e['aspectstance_mean'])} ± {_fmt(e['aspectstance_std'])}"
        if has_base:
            lines.append(
                f"| {e['display_name']} | {cell} | {_fmt(e['base_mean'])} ± {_fmt(e['base_std'])} | "
                f"{_fmt(e['delta'], sign=True)} | {e['seeds_with_positive_gain']}/{len(seeds)} |"
            )
        else:
            lines.append(f"| {e['display_name']} | {cell} |")
    if has_base:
        lines.append(
            f"| **Target average** | **{_fmt(avg['aspectstance'])}** ± {_fmt(avg['aspectstance_std_over_seeds'])} | "
            f"**{_fmt(avg['base'])}** ± {_fmt(avg['base_std_over_seeds'])} | **{_fmt(avg['delta'], sign=True)}** | |"
        )
    else:
        lines.append(f"| **Target average** | **{_fmt(avg['aspectstance'])}** |")
    lines.append("")
    lines.append("Entries are means ± standard deviation over the seeds.")

    if "random_best" in avg:
        lines += ["", "## Clustering-strategy control (layout of Table 4)", ""]
        lines += ["| Clustering | F1_avg | Δ |", "|---|---:|---:|"]
        lines.append(f"| K-means (AspectStance) | **{_fmt(avg['aspectstance'])}** | -- |")
        lines.append(
            f"| Random, best of {avg['random_n_per_target']} | {_fmt(avg['random_best'])} | "
            f"{_fmt(avg['random_best'] - avg['aspectstance'], sign=True)} |"
        )
        if has_base:
            lines.append(f"| None (Base Method) | {_fmt(avg['base'])} | {_fmt(-avg['delta'], sign=True)} |")
        lines.append("")
        lines.append(
            f"Full distribution of the random runs (not in the paper's table): mean "
            f"{_fmt(avg['random_mean'])} over all {avg['random_n_per_target']} configurations per target."
        )

    if per_target and "k_per_seed" in per_target[0]:
        lines += ["", "## Induced inventories (Tables 5 and 6, K and silhouette)", ""]
        lines += [
            "| Target | K (mode) | K stable over seeds | Cosine silhouette | Largest cluster share |",
            "|---|---:|:---:|---:|---:|",
        ]
        for e in per_target:
            lines.append(
                f"| {e['display_name']} | {e['k_mode']} | {'yes' if e['k_stable'] else 'no: ' + str(e['k_per_seed'])} | "
                f"{_fmt(e['silhouette_mean'], 2)} ± {_fmt(e['silhouette_std'], 2)} | {_fmt(e['largest_cluster_share'])}% |"
            )

    if "relabelled" in avg:
        lines += ["", "## Invariance checks (Section 6.2)", ""]
        lines += ["| Check | F1_avg | Δ vs AspectStance |", "|---|---:|---:|"]
        lines.append(
            f"| Relabelled cluster indices | {_fmt(avg['relabelled'])} | {_fmt(avg['relabelled'] - avg['aspectstance'], 2, sign=True)} |"
        )
        lines.append(
            f"| Permuted one-hot columns | {_fmt(avg['permuted'])} | {_fmt(avg['permuted'] - avg['aspectstance'], 2, sign=True)} |"
        )

    if "pooled_f_micro" in summary:
        lines += ["", "## Pooled score (F-micro_T, for reference)", ""]
        pooled = summary["pooled_f_micro"]
        lines.append(
            ", ".join(f"{name}: {_fmt(value)}" for name, value in pooled.items())
        )
    if "min_train_routing_agreement" in summary:
        lines += [
            "",
            "## Sanity checks",
            "",
            f"- Routing the training posts with Eq. (12) reproduces their K-means assignments in "
            f"{100 * summary['min_train_routing_agreement']:.2f}% of cases (minimum over runs).",
            f"- Summed run time of all (target, seed) jobs: {summary['total_compute_seconds'] / 60:.1f} minutes.",
        ]
    return "\n".join(lines) + "\n"


def write_summary(summary: Dict[str, Any], results_dir: str | Path, title: Optional[str] = None) -> None:
    results_dir = Path(results_dir)
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (results_dir / "summary.md").write_text(
        to_markdown(summary, title or "AspectStance results"), encoding="utf-8"
    )
