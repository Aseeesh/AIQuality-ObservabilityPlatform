#!/usr/bin/env bash
# Trigger an evaluation pass via the quality-evaluator service.
# Usage: run-evaluation.sh [dataset.jsonl]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$SCRIPT_DIR/../python-services/quality-evaluator"

cd "$EVAL_DIR"
python3 -m evaluator.runner "$@"
