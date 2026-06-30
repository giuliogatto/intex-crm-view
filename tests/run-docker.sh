#!/usr/bin/env bash
# Run prompt regression tests inside the intex-api Docker container (Python 3.11).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${INTEX_API_CONTAINER:-intex-api}"
REFERENCE_DATE="${PROMPT_TEST_REFERENCE_DATE:-2026-06-30}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Container '$CONTAINER' is not running."
  echo "Start the backend first:"
  echo "  cd backend && docker compose up -d"
  exit 1
fi

echo "Running prompt regression tests in container '$CONTAINER' (reference date: $REFERENCE_DATE)"

docker exec \
  -e PROMPT_TEST_REFERENCE_DATE="$REFERENCE_DATE" \
  -w /tests \
  "$CONTAINER" \
  bash -c "pip install -q -r requirements.txt && python -m pytest $*"
