"""The evaluation protocol of the paper (Sections 5.3, 5.4 and 6).

For every target and every seed (ten seeds by default):

1. **AspectStance** -- UMAP, the silhouette sweep, K-means and the ensemble are refitted with the
   seed; test posts are routed through the frozen centroids (RQ1, RQ2, RQ4).
2. **Base Method** -- the same ensemble on v alone, sharing the glosses, the embeddings and the
   UMAP mapping fitted in the same run; the one-hot block is the only design difference.
3. **Invariance checks** -- the cluster indices are relabelled consistently in training and test,
   and the one-hot columns are permuted (Section 6.2).
4. **Random-clustering control** (RQ3) -- the K-means partition is replaced by a uniformly random
   assignment to K clusters, K = 5..20, ten draws per K: 160 configurations per target. Centroids
   are computed on the L2-normalised representation and test posts are routed to the nearest one.
   Draw j reuses the representation of the j-th seeded run, so every component other than the
   partition is unchanged. The per-target *maximum* over the 160 runs is reported, as in the paper.

Glosses and embeddings are computed once and reused by every run.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .classifier import SoftVotingEnsemble, with_cluster_feature
from .clustering import NearestCentroidRouter, centroids_from_labels, random_partition
from .config import ExperimentConfig
from .data import slugify
from .metrics import f1_avg
from .model import AspectStanceModel
from .representation import l2_normalise

logger = logging.getLogger(__name__)

ASPECTSTANCE = "AspectStance"
BASE = "Base"
RELABELLED = "AspectStance (relabelled clusters)"
PERMUTED = "AspectStance (permuted one-hot columns)"


@dataclass
class TargetData:
    """Row-aligned arrays of one target's training and test posts."""

    target: str
    train_ids: np.ndarray
    test_ids: np.ndarray
    post_train: np.ndarray
    gloss_train: np.ndarray
    post_test: np.ndarray
    gloss_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray


def build_target_data(
    frame: pd.DataFrame, post_embeddings: np.ndarray, gloss_embeddings: np.ndarray, target: str
) -> TargetData:
    """Slice the canonical table and the two embedding matrices for one target."""
    if not (len(frame) == len(post_embeddings) == len(gloss_embeddings)):
        raise ValueError("The table and both embedding matrices must be row-aligned")
    target_mask = (frame["target"] == target).to_numpy()
    train = target_mask & (frame["split"] == "train").to_numpy()
    test = target_mask & (frame["split"] == "test").to_numpy()
    if not train.any() or not test.any():
        raise ValueError(f"Target '{target}' needs both a training and a test split")
    return TargetData(
        target=target,
        train_ids=frame.loc[train, "id"].to_numpy(),
        test_ids=frame.loc[test, "id"].to_numpy(),
        post_train=post_embeddings[train],
        gloss_train=gloss_embeddings[train],
        post_test=post_embeddings[test],
        gloss_test=gloss_embeddings[test],
        y_train=frame.loc[train, "label"].to_numpy(dtype=object),
        y_test=frame.loc[test, "label"].to_numpy(dtype=object),
    )


def assign_random_draws(seeds: Sequence[int], draws_per_k: int) -> Dict[int, List[int]]:
    """Draw j of the random control reuses the representation of seed ``seeds[j % len(seeds)]``."""
    mapping: Dict[int, List[int]] = {seed: [] for seed in seeds}
    for draw in range(draws_per_k):
        mapping[seeds[draw % len(seeds)]].append(draw)
    return mapping


def _metric_row(target: str, seed: int, method: str, y_true, y_pred, **extra) -> Dict[str, Any]:
    row = {"target": target, "seed": seed, "method": method}
    row.update(extra)
    row.update(f1_avg(y_true, y_pred))
    return row


def run_target_seed(
    data: TargetData,
    seed: int,
    config: ExperimentConfig,
    random_draws: Sequence[int] = (),
) -> Dict[str, Any]:
    """Run every arm of the protocol for one target and one seed."""
    start = time.time()
    target = data.target

    # ---- AspectStance ------------------------------------------------------------------------
    model = AspectStanceModel(
        target, config.umap, config.clustering, random_state=seed, use_cluster_feature=True
    ).fit(data.post_train, data.gloss_train, data.y_train)
    v_train = model.train_representation_
    v_test = model.represent(data.post_test, data.gloss_test)
    vhat_train, vhat_test = l2_normalise(v_train), l2_normalise(v_test)
    k = model.n_aspects
    c_train = model.train_clusters_
    prediction = model.predict_representation(v_test)
    c_test = prediction.clusters
    # Eq. (12) reproduces the training assignments once K-means has converged.
    routing_agreement = float(np.mean(model.router_.route(vhat_train) == c_train))

    metrics = [
        _metric_row(
            target, seed, ASPECTSTANCE, data.y_test, prediction.labels,
            k=k, silhouette=model.silhouette,
        )
    ]
    predictions = pd.DataFrame(
        {
            "id": data.test_ids,
            "gold": data.y_test,
            "cluster": c_test,
            "pred_aspectstance": prediction.labels,
        }
    )

    # ---- Base Method ---------------------------------------------------------------------------
    if config.run_base:
        base = SoftVotingEnsemble(random_state=seed).fit(v_train, data.y_train)
        base_pred = base.predict(v_test)
        metrics.append(_metric_row(target, seed, BASE, data.y_test, base_pred))
        predictions["pred_base"] = base_pred

    # ---- Invariance checks ---------------------------------------------------------------------
    invariance = []
    if config.run_invariance_checks:
        rng = np.random.default_rng([seed, 2016])
        relabel = rng.permutation(k)
        ensemble = SoftVotingEnsemble(random_state=seed).fit(
            with_cluster_feature(v_train, relabel[c_train], k), data.y_train
        )
        relabelled = ensemble.predict(with_cluster_feature(v_test, relabel[c_test], k))
        order = rng.permutation(k)
        ensemble = SoftVotingEnsemble(random_state=seed).fit(
            with_cluster_feature(v_train, c_train, k, column_order=order), data.y_train
        )
        permuted = ensemble.predict(with_cluster_feature(v_test, c_test, k, column_order=order))
        for method, pred in ((RELABELLED, relabelled), (PERMUTED, permuted)):
            row = _metric_row(target, seed, method, data.y_test, pred)
            row["agreement_with_aspectstance"] = float(np.mean(pred == prediction.labels))
            invariance.append(row)

    # ---- Random-clustering control -------------------------------------------------------------
    random_rows = []
    rc = config.random_control
    if config.run_random_control:
        for draw in random_draws:
            for k_random in range(rc.k_min, rc.k_max + 1):
                rng = np.random.default_rng([draw, k_random, 7])
                labels = random_partition(len(v_train), k_random, rng)
                router = NearestCentroidRouter(centroids_from_labels(vhat_train, labels, k_random))
                routed = router.route(vhat_test)
                ensemble = SoftVotingEnsemble(random_state=seed).fit(
                    with_cluster_feature(v_train, labels, k_random), data.y_train
                )
                pred = ensemble.predict(with_cluster_feature(v_test, routed, k_random))
                random_rows.append(
                    _metric_row(target, seed, "Random clustering", data.y_test, pred, draw=draw, k=k_random)
                )

    sizes_train = np.bincount(c_train, minlength=k)
    sizes_test = np.bincount(c_test, minlength=k)
    inventory = [
        {
            "target": target,
            "seed": seed,
            "k": k,
            "silhouette": model.silhouette,
            "cluster": cluster,
            "n_train": int(sizes_train[cluster]),
            "share_train": 100.0 * sizes_train[cluster] / len(c_train),
            "n_test": int(sizes_test[cluster]),
            **{
                f"train_{label.lower()}": int(np.sum((c_train == cluster) & (data.y_train == label)))
                for label in sorted(set(data.y_train))
            },
        }
        for cluster in range(k)
    ]
    sweep = [
        {"target": target, "seed": seed, "k": kk, "silhouette": score}
        for kk, score in model.sweep_.scores.items()
    ]
    assignments = pd.concat(
        [
            pd.DataFrame({"id": data.train_ids, "split": "train", "cluster": c_train}),
            pd.DataFrame({"id": data.test_ids, "split": "test", "cluster": c_test}),
        ],
        ignore_index=True,
    )
    return {
        "target": target,
        "seed": seed,
        "metrics": metrics,
        "invariance": invariance,
        "random": random_rows,
        "inventory": inventory,
        "sweep": sweep,
        "predictions": predictions,
        "assignments": assignments,
        "routing_agreement": routing_agreement,
        "seconds": time.time() - start,
    }


def run_experiments(
    frame: pd.DataFrame,
    post_embeddings: np.ndarray,
    gloss_embeddings: np.ndarray,
    config: ExperimentConfig,
    out_dir: str | Path,
    progress: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full protocol and write every artefact to ``out_dir``; returns the summary."""
    from joblib import Parallel, delayed

    from .report import summarise, write_summary

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = config.targets or sorted(frame.loc[frame["split"] == "test", "target"].unique())
    data = {t: build_target_data(frame, post_embeddings, gloss_embeddings, t) for t in targets}
    draws = assign_random_draws(config.seeds, config.random_control.draws_per_k)
    jobs = [(t, s) for t in targets for s in config.seeds]
    logger.info("Running %d (target, seed) jobs with n_jobs=%d", len(jobs), config.n_jobs)

    tasks = (delayed(run_target_seed)(data[t], s, config, draws[s]) for t, s in jobs)
    runner = Parallel(n_jobs=config.n_jobs, return_as="generator_unordered")
    outputs = []
    bar = None
    if progress:
        from tqdm.auto import tqdm

        bar = tqdm(total=len(jobs), desc="target x seed")
    for output in runner(tasks):
        outputs.append(output)
        if bar is not None:
            bar.update(1)
            bar.set_postfix_str(f"{output['target']} seed={output['seed']} K={output['inventory'][0]['k']}")
    if bar is not None:
        bar.close()
    outputs.sort(key=lambda o: (targets.index(o["target"]), o["seed"]))

    # ---- write artefacts -------------------------------------------------------------------------
    def frame_of(key: str) -> pd.DataFrame:
        return pd.DataFrame([row for o in outputs for row in o[key]])

    metrics = frame_of("metrics")
    metrics.to_csv(out_dir / "metrics_per_seed.csv", index=False)
    frame_of("sweep").to_csv(out_dir / "sweep_scores.csv", index=False)
    frame_of("inventory").to_csv(out_dir / "inventory.csv", index=False)
    if config.run_invariance_checks:
        frame_of("invariance").to_csv(out_dir / "invariance.csv", index=False)
    if config.run_random_control:
        frame_of("random").to_csv(out_dir / "random_control_runs.csv", index=False)
    pd.DataFrame(
        [
            {"target": o["target"], "seed": o["seed"], "seconds": o["seconds"],
             "train_routing_agreement": o["routing_agreement"]}
            for o in outputs
        ]
    ).to_csv(out_dir / "runs.csv", index=False)

    pooled_rows = []
    for seed in config.seeds:
        pooled = pd.concat([o["predictions"] for o in outputs if o["seed"] == seed], ignore_index=True)
        row = {"seed": seed, "aspectstance": f1_avg(pooled["gold"], pooled["pred_aspectstance"])["f1_avg"]}
        if "pred_base" in pooled:
            row["base"] = f1_avg(pooled["gold"], pooled["pred_base"])["f1_avg"]
        pooled_rows.append(row)
    pd.DataFrame(pooled_rows).to_csv(out_dir / "pooled_f_micro_per_seed.csv", index=False)

    for o in outputs:
        slug = slugify(o["target"])
        for kind in ("predictions", "assignments"):
            path = out_dir / kind / slug / f"seed{o['seed']}.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            o[kind].to_csv(path, index=False)

    run_info = {"config": config.to_dict(), "targets": targets}
    run_info.update(metadata or {})
    (out_dir / "run_config.json").write_text(json.dumps(run_info, indent=2), encoding="utf-8")

    summary = summarise(out_dir)
    write_summary(summary, out_dir, title=title)
    return summary
