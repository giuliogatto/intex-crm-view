#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_FILE="${REPO_ROOT}/backup-$(date +%Y-%m-%d_%H-%M-%S).sql.gz"

cd "${REPO_ROOT}/data"

docker compose exec -T timescaledb-intex pg_dump -U postgres \
  --exclude-schema=_timescaledb_catalog \
  --exclude-schema=_timescaledb_config \
  --exclude-schema=_timescaledb_internal \
  postgres 2>/dev/null | gzip > "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"
ls -lh "${BACKUP_FILE}"
