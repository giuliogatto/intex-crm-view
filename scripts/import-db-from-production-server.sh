#!/usr/bin/env bash
# Copia un dump SQL.gz dal server di produzione, svuota il DB locale e lo importa.
#
# Uso:
#   ./scripts/import-db-from-production-server.sh backup-prod-2026-10-29.sql.gz
#
# Variabili opzionali:
#   SSH_KEY=~/github_deploy_key
#   SSH_HOST=debian@57.131.22.138
#   REMOTE_DIR=/home/debian
#   CONTAINER=intexdata
#   LOCAL_DIR=<repo root>   # dove salvare il dump scaricato

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SSH_KEY="${SSH_KEY:-$HOME/github_deploy_key}"
SSH_HOST="${SSH_HOST:-debian@57.131.22.138}"
REMOTE_DIR="${REMOTE_DIR:-/home/debian}"
CONTAINER="${CONTAINER:-intexdata}"
LOCAL_DIR="${LOCAL_DIR:-$REPO_ROOT}"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 <nome-file-backup.sql.gz>

Esempio:
  $0 backup-prod-2026-10-29.sql.gz

Il file viene cercato su ${SSH_HOST}:${REMOTE_DIR}/ e importato nel container ${CONTAINER}.
EOF
  exit 1
}

[[ $# -eq 1 ]] || usage
REMOTE_FILE="$1"
[[ "$REMOTE_FILE" == *.sql.gz ]] || die "atteso un file .sql.gz, ricevuto: $REMOTE_FILE"

command -v docker >/dev/null || die "docker non trovato"
command -v scp >/dev/null || die "scp non trovato"
command -v gunzip >/dev/null || die "gunzip non trovato"
[[ -f "$SSH_KEY" ]] || die "chiave SSH non trovata: $SSH_KEY"
docker inspect "$CONTAINER" >/dev/null 2>&1 || die "container non trovato: $CONTAINER"

LOCAL_FILE="${LOCAL_DIR}/$(basename "$REMOTE_FILE")"
REMOTE_PATH="${REMOTE_DIR%/}/${REMOTE_FILE}"

# --- 1. SCP dal server ---
log "Scarico ${SSH_HOST}:${REMOTE_PATH} → ${LOCAL_FILE}"
scp -i "$SSH_KEY" "${SSH_HOST}:${REMOTE_PATH}" "$LOCAL_FILE"
[[ -s "$LOCAL_FILE" ]] || die "download fallito o file vuoto: $LOCAL_FILE"
# gzip vuoto tipicamente ~20 byte
LOCAL_SIZE="$(wc -c < "$LOCAL_FILE" | tr -d ' ')"
[[ "$LOCAL_SIZE" -gt 100 ]] || die "file troppo piccolo (${LOCAL_SIZE} byte) — dump probabilmente vuoto/corrotto"
log "Download OK ($(ls -lh "$LOCAL_FILE" | awk '{print $5}'))"

# --- 2. Svuota DB locale ---
log "Svuoto database postgres nel container ${CONTAINER}"
docker exec -i "$CONTAINER" psql -U postgres -d template1 <<'EOF'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'postgres' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS postgres;
CREATE DATABASE postgres;
EOF

# --- 3. Import dump ---
log "Importo dump in ${CONTAINER} (filtro _timescaledb + \\restrict)"
(
  echo "SET session_replication_role = replica;"
  gunzip -c "$LOCAL_FILE" \
    | grep -v '^pg_dump:' \
    | grep -vE '^\\(un)?restrict' \
    | awk '
{ gsub(/\r$/, "") }
/^COPY _timescaledb/ { skip=1; next }
skip && /^\\.$/ { skip=0; next }
skip { next }
/SELECT pg_catalog.setval/ && /_timescaledb/ { next }
{ print }
'
  echo "SET session_replication_role = DEFAULT;"
) | docker exec -i "$CONTAINER" psql -U postgres -d postgres -v ON_ERROR_STOP=1

log "Verifica conteggi tabelle principali"
docker exec -i "$CONTAINER" psql -U postgres -d postgres -c "
SELECT 'stagioni' AS t, count(*) FROM stagioni
UNION ALL SELECT 'fatture_testate', count(*) FROM fatture_testate
UNION ALL SELECT 'fatture_righe', count(*) FROM fatture_righe
UNION ALL SELECT 'ddt_testate', count(*) FROM ddt_testate
UNION ALL SELECT 'ddt_righe', count(*) FROM ddt_righe;
"

log "Elimino dump locale: ${LOCAL_FILE}"
rm -f "$LOCAL_FILE"

log "Import completato."
