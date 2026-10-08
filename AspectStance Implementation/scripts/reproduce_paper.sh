#!/usr/bin/env bash
# Reproduce every number of the paper: AspectStance, Base Method, random-clustering control,
# invariance checks, aspect names and both prompting baselines, on P-Stance and SemEval-2016.
#
#   export OPENAI_API_KEY=sk-...
#   PSTANCE_DIR=data/PStance SEMEVAL_DIR=data/SemEval2016 bash scripts/reproduce_paper.sh
#
# PSTANCE_DIR must contain raw_{train,test}_{trump,biden,bernie}.csv.
# SEMEVAL_TRAIN / SEMEVAL_TEST list the SemEval-2016 files (space-separated); the defaults are the
# official trial + training files and the Subtask A test file with gold labels.
set -euo pipefail

cd "$(dirname "$0")/.."
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY first}"
PSTANCE_DIR="${PSTANCE_DIR:-data/PStance}"
SEMEVAL_DIR="${SEMEVAL_DIR:-data/SemEval2016}"
SEMEVAL_TRAIN="${SEMEVAL_TRAIN:-$SEMEVAL_DIR/semeval2016-task6-trialdata.txt $SEMEVAL_DIR/semeval2016-task6-trainingdata.txt}"
SEMEVAL_TEST="${SEMEVAL_TEST:-$SEMEVAL_DIR/SemEval2016-Task6-subtaskA-testdata-gold.txt}"
JOBS="${JOBS:-4}"
AS="python -m aspectstance"

run_dataset () {
  local ws="$1"
  $AS enrich    -w "$ws"                         # GPT-6 Luna glosses, medium reasoning effort
  $AS embed     -w "$ws"                         # text-embedding-3-large, post and gloss
  $AS run       -w "$ws" --jobs "$JOBS"          # 10 seeds: AspectStance, Base, random control, invariance
  $AS name      -w "$ws" --results openai --seed 0
  $AS baselines -w "$ws" --mode zero-shot --passes 10
  $AS baselines -w "$ws" --mode few-shot  --passes 10
}

$AS prepare -w workspace/pstance --dataset pstance --pstance-dir "$PSTANCE_DIR"
run_dataset workspace/pstance

# shellcheck disable=SC2086  # the file lists are meant to be split into arguments
$AS prepare -w workspace/semeval --dataset semeval2016 --semeval-train $SEMEVAL_TRAIN --semeval-test $SEMEVAL_TEST
run_dataset workspace/semeval

echo "Summaries: workspace/pstance/results/openai/summary.md and workspace/semeval/results/openai/summary.md"
