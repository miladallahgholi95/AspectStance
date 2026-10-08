"""Command-line interface: ``python -m aspectstance <command>``.

Stages (each reads and writes the same workspace directory)::

    prepare    load P-Stance or SemEval-2016 into the canonical table
    enrich     generate one target-conditioned gloss per post (GPT-6 Luna, cached)
    embed      encode posts and glosses (text-embedding-3-large, cached)
    run        ten-seed evaluation: AspectStance, Base Method, random control, invariance checks
    report     re-render the summary tables of a finished run
    name       post hoc cluster naming for one seed (GPT-6 Luna)
    baselines  zero-shot and retrieval-augmented few-shot prompting baselines
    fit        train a deployable per-target model on the training split
    predict    stance label + aspect cluster for new posts with a saved model
    released   summarise the released aspect assignments and check them against the paper
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_REASONING_EFFORT,
    AspectStanceConfig,
    LLMConfig,
    parse_seeds,
)

logger = logging.getLogger("aspectstance")


# ------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------


def _workspace(args):
    from .workspace import Workspace

    return Workspace(args.workspace)


def _llm(args, workspace):
    from .llm import LLMClient

    config = LLMConfig(
        model=args.model,
        reasoning_effort=args.reasoning_effort or None,
        api=args.api,
        workers=args.workers,
    )
    return LLMClient(config, cache=workspace.cache())


def _add_llm_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("language model (paper: GPT-6 Luna, medium reasoning effort)")
    group.add_argument("--model", default=DEFAULT_LLM_MODEL, help="API model id (default: %(default)s)")
    group.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT,
                       help="reasoning effort sent with every call; '' to omit (default: %(default)s)")
    group.add_argument("--api", choices=("responses", "chat"), default="responses",
                       help="OpenAI API flavour (default: %(default)s)")
    group.add_argument("--workers", type=int, default=8, help="concurrent requests (default: %(default)s)")


def _protocol(workspace) -> dict:
    path = workspace.root / "protocol.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _resolve_embeddings(workspace, requested: Optional[str]) -> str:
    available = workspace.available_embeddings()
    if requested:
        return requested
    if len(available) == 1:
        return available[0]
    if "openai" in available:
        return "openai"
    raise SystemExit(f"Choose --embeddings among {available or 'nothing yet: run `embed` first'}")


# ------------------------------------------------------------------------------------------------
# commands
# ------------------------------------------------------------------------------------------------


def cmd_prepare(args) -> None:
    from .data import load_pstance, load_semeval2016, make_holdout_split, summarise_splits

    ws = _workspace(args)
    if args.dataset == "pstance":
        if not args.pstance_dir:
            raise SystemExit("--pstance-dir is required for P-Stance")
        frame = load_pstance(args.pstance_dir, include_val=args.include_val)
        sources = [str(args.pstance_dir)]
    else:
        if not args.semeval_train:
            raise SystemExit("--semeval-train is required for SemEval-2016")
        frame = load_semeval2016(args.semeval_train, args.semeval_test or [])
        sources = [str(p) for p in args.semeval_train + (args.semeval_test or [])]

    protocol = "official training and test splits"
    if args.dataset == "semeval2016":
        numeric = frame.loc[frame["split"] == "train", "id"].str.extract(r"semeval2016-(\d+)$")[0].dropna()
        if not (numeric.astype(int) <= 100).any():
            logger.warning(
                "No SemEval-2016 trial posts (IDs 1-100) in the training files; the paper's training "
                "split includes them (pass the trial file to --semeval-train)."
            )
            protocol += " (training split without the 100 trial posts)"
    if args.holdout_fraction:
        if (frame["split"] == "test").any():
            raise SystemExit("An official test split is present; --holdout-fraction is only for data without one")
        frame = make_holdout_split(frame, args.holdout_fraction, args.holdout_seed)
        protocol = (
            f"HOLD-OUT (not the paper's protocol): {args.holdout_fraction:.0%} of each target's official "
            f"training split, stratified by label (seed {args.holdout_seed}), is used as the test split"
        )
    elif not (frame["split"] == "test").any():
        logger.warning("No test split found: `run` needs one (or re-run with --holdout-fraction)")

    ws.save_dataset(frame)
    (ws.root / "protocol.json").write_text(
        json.dumps({"dataset": args.dataset, "protocol": protocol, "sources": sources}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {ws.dataset_path} ({len(frame)} posts). Protocol: {protocol}")
    print(summarise_splits(frame).to_string())


def cmd_enrich(args) -> None:
    from .enrichment import generate_glosses

    ws = _workspace(args)
    frame = ws.load_dataset()
    if args.limit:
        frame = frame.head(args.limit)
    llm = _llm(args, ws) if args.backend == "openai" else None
    glosses = generate_glosses(frame["text"].tolist(), frame["target"].tolist(), args.backend, llm)
    if args.limit:
        print("\n\n".join(f"[{t}] {x}\n  -> {g}" for t, x, g in zip(frame["target"], frame["text"], glosses)))
        print("\n--limit given: glosses were cached but glosses.csv was not written.")
        return
    model = args.model if args.backend == "openai" else "template-v1"
    ws.save_glosses(frame["id"], glosses, args.backend, model)
    lengths = pd.Series([len(g.split()) for g in glosses])
    print(f"Wrote {ws.glosses_path}: {len(glosses)} glosses, median length {lengths.median():.0f} words")


def cmd_embed(args) -> None:
    from .embeddings import LSAEmbedder, build_embedder

    ws = _workspace(args)
    frame = ws.load_dataset()
    glosses = ws.load_glosses(frame)
    embedder = build_embedder(args.backend, model=args.embedding_model, batch_size=args.batch_size,
                              cache=ws.cache() if args.backend == "openai" else None)
    meta = {"backend": args.backend, "gloss_backend": glosses["gloss_backend"].iloc[0],
            "gloss_model": glosses["gloss_model"].iloc[0]}
    if isinstance(embedder, LSAEmbedder):
        train = (frame["split"] == "train").to_numpy()
        embedder.fit(frame.loc[train, "text"].tolist() + glosses.loc[train, "gloss"].tolist())
        meta["fitted_on"] = "training split (posts and glosses) only"
        import joblib

        ws.embeddings_dir(args.backend).mkdir(parents=True, exist_ok=True)
        joblib.dump(embedder, ws.embeddings_dir(args.backend) / "encoder.joblib")
    if args.backend == "openai":
        meta["model"] = args.embedding_model
    elif args.backend == "wordllama":
        meta["model"] = "wordllama l2_supercat 256-d"
    post = embedder.embed(frame["text"].tolist())
    gloss = embedder.embed(glosses["gloss"].tolist())
    ws.save_embeddings(args.backend, frame["id"].tolist(), post, gloss, meta)
    print(f"Wrote {ws.embeddings_dir(args.backend)}: post {post.shape}, gloss {gloss.shape}")


def _experiment_config(args):
    config = AspectStanceConfig.from_yaml(args.config) if args.config else AspectStanceConfig()
    exp = config.experiment
    if args.seeds:
        exp.seeds = parse_seeds(args.seeds)
    if args.jobs:
        exp.n_jobs = args.jobs
    if args.targets:
        exp.targets = args.targets
    if args.no_random_control:
        exp.run_random_control = False
    if args.no_invariance:
        exp.run_invariance_checks = False
    return exp


def cmd_run(args) -> None:
    from .experiment import run_experiments
    from .report import to_markdown

    ws = _workspace(args)
    frame = ws.load_dataset()
    backend = _resolve_embeddings(ws, args.embeddings)
    post, gloss, meta = ws.load_embeddings(backend, frame["id"].tolist())
    exp = _experiment_config(args)
    name = args.name or backend
    out = ws.results_dir(name)
    metadata = {
        "protocol": _protocol(ws).get("protocol", "unknown"),
        "dataset": _protocol(ws).get("dataset", "unknown"),
        "backends": {
            "gloss": f"{meta.get('gloss_backend')} ({meta.get('gloss_model')})",
            "embedding": f"{meta.get('backend')} ({meta.get('model', '-')})",
        },
    }
    title = args.title or f"AspectStance results ({name})"
    summary = run_experiments(frame, post, gloss, exp, out, progress=not args.quiet, metadata=metadata, title=title)
    print(to_markdown(summary, title=title))
    print(f"Artefacts written to {out}")


def cmd_report(args) -> None:
    from .report import summarise, to_markdown, write_summary

    summary = summarise(args.results)
    write_summary(summary, args.results, title=args.title)
    print(to_markdown(summary, title=args.title or "AspectStance results"))


def cmd_name(args) -> None:
    from .naming import name_clusters

    ws = _workspace(args)
    frame = ws.load_dataset()
    results = ws.results_dir(args.results)
    llm = _llm(args, ws)
    tables = []
    for path in sorted((results / "assignments").glob(f"*/seed{args.seed}.csv")):
        assignments = pd.read_csv(path, dtype={"id": str})
        train = assignments[assignments["split"] == "train"].merge(frame[["id", "text", "target"]], on="id")
        target = train["target"].iloc[0]
        tables.append(name_clusters(train["text"], train["cluster"], target, llm, args.max_posts, args.seed))
    if not tables:
        raise SystemExit(f"No assignments for seed {args.seed} in {results}")
    names = pd.concat(tables, ignore_index=True)
    out = results / f"aspect_names_seed{args.seed}.csv"
    names.to_csv(out, index=False)
    print(names.to_string(index=False, max_colwidth=90))
    print(f"Wrote {out}")


def cmd_baselines(args) -> None:
    from .baselines import run_prompting_baseline, score_prompting
    from .metrics import f_macro_t

    ws = _workspace(args)
    frame = ws.load_dataset()
    post = None
    if args.mode == "few-shot":
        backend = _resolve_embeddings(ws, args.embeddings)
        post, _, _ = ws.load_embeddings(backend, frame["id"].tolist())
    llm = _llm(args, ws)
    predictions = run_prompting_baseline(frame, args.mode, llm, args.passes, post, args.per_label)
    scores = score_prompting(predictions)
    out = ws.results_dir(f"baseline-{args.mode}")
    out.mkdir(parents=True, exist_ok=True)
    predictions.drop(columns=["response"]).to_csv(out / "predictions.csv", index=False)
    scores.to_csv(out / "scores_per_pass.csv", index=False)
    per_target = scores.groupby("target")["f1_avg"].mean()
    print(per_target.round(1).to_string())
    print(f"Target average (F-macro_T), mean over {args.passes} passes: {f_macro_t(per_target):.1f}")
    print(f"Invalid responses: {(predictions['prediction'] == 'INVALID').mean():.2%}")


def cmd_fit(args) -> None:
    from .data import slugify
    from .model import AspectStanceModel

    ws = _workspace(args)
    frame = ws.load_dataset()
    backend = _resolve_embeddings(ws, args.embeddings)
    post, gloss, meta = ws.load_embeddings(backend, frame["id"].tolist())
    config = AspectStanceConfig.from_yaml(args.config) if args.config else AspectStanceConfig()
    targets = args.targets or sorted(frame["target"].unique())
    for target in targets:
        mask = ((frame["target"] == target) & (frame["split"] == "train")).to_numpy()
        model = AspectStanceModel(
            target, config.experiment.umap, config.experiment.clustering, random_state=args.seed
        ).fit(post[mask], gloss[mask], frame.loc[mask, "label"].to_numpy(dtype=object))
        model.embedding_meta = meta
        if meta.get("backend") == "lsa":
            import joblib

            model.encoder = joblib.load(ws.embeddings_dir(backend) / "encoder.joblib")
        if args.names:
            names = pd.read_csv(args.names)
            names = names[names["target"] == target]
            model.aspect_names = dict(zip(names["cluster"].astype(int), names["name"]))
        path = model.save(ws.model_path(slugify(target), args.seed))
        print(f"{target}: K={model.n_aspects} (silhouette {model.silhouette:.3f}) -> {path}")


def cmd_predict(args) -> None:
    from .embeddings import build_embedder
    from .enrichment import generate_glosses
    from .model import AspectStanceModel

    model = AspectStanceModel.load(args.model_path)
    meta = getattr(model, "embedding_meta", {})
    posts = pd.read_csv(args.input, keep_default_na=False)
    column = args.text_column
    texts = posts[column].astype(str).tolist()
    targets = [model.target] * len(texts)

    gloss_backend = meta.get("gloss_backend", "openai")
    workspace = None
    if gloss_backend == "openai" or meta.get("backend") == "openai":
        from .workspace import Workspace

        workspace = Workspace(args.cache_dir)
    llm = _llm(args, workspace) if gloss_backend == "openai" else None
    glosses = generate_glosses(texts, targets, gloss_backend, llm, progress=False)
    if meta.get("backend") == "lsa":
        embedder = model.encoder
    else:
        embedder = build_embedder(meta.get("backend", "openai"), model=meta.get("model", DEFAULT_EMBEDDING_MODEL),
                                  cache=workspace.cache() if workspace else None)
    prediction = model.predict(embedder.embed(texts, progress=False), embedder.embed(glosses, progress=False))
    out = posts.copy()
    out["gloss"] = glosses
    out["stance"] = prediction.labels
    out["aspect_cluster"] = prediction.clusters
    if prediction.aspect_names is not None:
        out["aspect_name"] = prediction.aspect_names
    for j, label in enumerate(prediction.classes):
        out[f"p_{label.lower()}"] = prediction.probabilities[:, j].round(4)
    if args.output:
        out.to_csv(args.output, index=False)
        print(f"Wrote {args.output}")
    else:
        print(out.drop(columns=["gloss"]).to_string(index=False, max_colwidth=80))


def cmd_released(args) -> None:
    from .released import check_released_inventories

    report = check_released_inventories(args.root)
    print(report)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}")


# ------------------------------------------------------------------------------------------------
# parser
# ------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aspectstance",
        description="AspectStance: unsupervised discovery of target-specific aspects for stance detection.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_workspace(p):
        p.add_argument("--workspace", "-w", required=True, help="workspace directory")
        return p

    p = with_workspace(sub.add_parser("prepare", help="load a benchmark into the canonical table"))
    p.add_argument("--dataset", choices=("pstance", "semeval2016"), required=True)
    p.add_argument("--pstance-dir", help="folder with raw_{train,val,test}_{trump,biden,bernie}.csv")
    p.add_argument("--include-val", action="store_true",
                   help="also load the P-Stance validation split (unused by every stage, as in the paper)")
    p.add_argument("--semeval-train", nargs="+", help="training file(s); add the trial file to match the paper")
    p.add_argument("--semeval-test", nargs="+", help="Subtask A test file(s) with gold labels")
    p.add_argument("--holdout-fraction", type=float, default=None,
                   help="only when no test split exists: stratified hold-out (NOT the paper's protocol)")
    p.add_argument("--holdout-seed", type=int, default=0)
    p.set_defaults(func=cmd_prepare)

    p = with_workspace(sub.add_parser("enrich", help="generate target-conditioned glosses"))
    p.add_argument("--backend", choices=("openai", "template"), default="openai",
                   help="'openai' = paper; 'template' = offline stand-in without background knowledge")
    p.add_argument("--limit", type=int, default=None, help="only gloss the first N posts and print them")
    _add_llm_arguments(p)
    p.set_defaults(func=cmd_enrich)

    p = with_workspace(sub.add_parser("embed", help="encode posts and glosses"))
    p.add_argument("--backend", choices=("openai", "wordllama", "lsa"), default="openai",
                   help="'openai' = paper (text-embedding-3-large); others are offline stand-ins")
    p.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    p.add_argument("--batch-size", type=int, default=256)
    p.set_defaults(func=cmd_embed)

    def experiment_args(p):
        p.add_argument("--embeddings", help="embedding backend folder to use (default: the only one)")
        p.add_argument("--config", help="YAML configuration (default: paper settings)")
        p.add_argument("--seeds", help="e.g. 0-9 (default: 0-9)")
        p.add_argument("--targets", nargs="+", help="subset of targets (full names)")
        return p

    p = with_workspace(experiment_args(sub.add_parser("run", help="ten-seed evaluation of every arm")))
    p.add_argument("--name", help="results sub-folder (default: embedding backend)")
    p.add_argument("--title", help="title of summary.md")
    p.add_argument("--jobs", type=int, default=1, help="parallel (target, seed) jobs")
    p.add_argument("--no-random-control", action="store_true", help="skip the 160-run random control")
    p.add_argument("--no-invariance", action="store_true", help="skip the invariance checks")
    p.add_argument("--quiet", action="store_true", help="no progress bar")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="re-render summary tables of a finished run")
    p.add_argument("results", help="results directory written by `run`")
    p.add_argument("--title", default=None)
    p.set_defaults(func=cmd_report)

    p = with_workspace(sub.add_parser("name", help="post hoc cluster naming (GPT-6 Luna)"))
    p.add_argument("--results", required=True, help="results sub-folder name used by `run`")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-posts", type=int, default=None, help="cap posts per cluster (default: all, as in the paper)")
    _add_llm_arguments(p)
    p.set_defaults(func=cmd_name)

    p = with_workspace(sub.add_parser("baselines", help="zero-shot / few-shot prompting baselines"))
    p.add_argument("--mode", choices=("zero-shot", "few-shot"), required=True)
    p.add_argument("--passes", type=int, default=10)
    p.add_argument("--per-label", type=int, default=5, help="retrieved examples per label (few-shot)")
    p.add_argument("--embeddings", help="embedding backend used for retrieval (paper: openai)")
    _add_llm_arguments(p)
    p.set_defaults(func=cmd_baselines)

    p = with_workspace(sub.add_parser("fit", help="train deployable per-target models"))
    p.add_argument("--embeddings", help="embedding backend folder to use")
    p.add_argument("--config", help="YAML configuration (default: paper settings)")
    p.add_argument("--targets", nargs="+")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--names", help="aspect_names_seed<k>.csv from `name`, attached to the model")
    p.set_defaults(func=cmd_fit)

    p = sub.add_parser("predict", help="stance + aspect for new posts with a saved model")
    p.add_argument("model_path", help="models/<target>/seed<k>.joblib written by `fit`")
    p.add_argument("--input", required=True, help="CSV with one post per row")
    p.add_argument("--text-column", default="text")
    p.add_argument("--output", help="CSV to write (default: print)")
    p.add_argument("--cache-dir", default=".aspectstance-cache", help="where API responses are cached")
    _add_llm_arguments(p)
    p.set_defaults(func=cmd_predict)

    p = sub.add_parser("released", help="check the released aspect assignments against the paper")
    p.add_argument("--root", default="../Clustering Results (Aspects)")
    p.add_argument("--output", help="also write the report to this Markdown file")
    p.set_defaults(func=cmd_released)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    args.func(args)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
