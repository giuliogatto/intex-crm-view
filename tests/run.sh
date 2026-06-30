#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/tests"

python3 -m pip install -q -r requirements.txt
python3 -m pip install -q -r "$ROOT/backend/requirements.txt"

if [[ -f "$ROOT/backend/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/backend/.env"
  set +a
fi

export PROMPT_TEST_REFERENCE_DATE="${PROMPT_TEST_REFERENCE_DATE:-2026-06-30}"

if [[ "${1:-}" == "--docker" ]]; then
  shift
  exec "$ROOT/tests/run-docker.sh" "$@"
fi

echo "Running prompt regression tests (sequential, reference date: $PROMPT_TEST_REFERENCE_DATE)"
python3 -m pytest "$@"
