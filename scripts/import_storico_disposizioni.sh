#!/usr/bin/env bash
# Import giornaliero EW1/EW2 (e opzionalmente storico_disposizioni) da CSV SFTP
# → TRUNCATE + \copy nel container Timescale.
#
# Atteso dopo l'export Windows (extract_upload_tables_storico*.py → SFTP):
#   /var/data_imports/intex/{timestamp}_ew1_testata_disposizioni.csv
#   /var/data_imports/intex/{timestamp}_ew2_righe_disposizioni.csv
#   /var/data_imports/intex/{timestamp}_storico_disposizioni.csv   (opzionale)
#
# Uso:
#   ./scripts/import_storico_disposizioni.sh
#   IMPORT_DIR=/altro/path ./scripts/import_storico_disposizioni.sh

set -euo pipefail

IMPORT_DIR="${IMPORT_DIR:-/var/data_imports/intex}"
CONTAINER="${CONTAINER:-data-timescaledb-intex-1}"
PSQL=(docker exec -i "$CONTAINER" psql -U postgres -d postgres -v ON_ERROR_STOP=1)

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

command -v docker >/dev/null || die "docker non trovato"
docker inspect "$CONTAINER" >/dev/null 2>&1 || die "container non trovato: $CONTAINER"
[[ -d "$IMPORT_DIR" ]] || die "cartella import assente: $IMPORT_DIR"

# --- Ultimo set EW1+EW2 con stesso timestamp ---
mapfile -t EW1_CANDIDATES < <(ls -1t "$IMPORT_DIR"/*_ew1_testata_disposizioni.csv 2>/dev/null || true)
[[ ${#EW1_CANDIDATES[@]} -gt 0 ]] || die "nessun CSV ew1 in $IMPORT_DIR"

EW1=""
EW2=""
TS=""
for candidate in "${EW1_CANDIDATES[@]}"; do
  base="$(basename "$candidate")"
  ts="${base%_ew1_testata_disposizioni.csv}"
  ew2_path="$IMPORT_DIR/${ts}_ew2_righe_disposizioni.csv"
  if [[ -f "$ew2_path" ]]; then
    EW1="$candidate"
    EW2="$ew2_path"
    TS="$ts"
    break
  fi
done

[[ -n "$EW1" && -n "$EW2" ]] || die "nessuna coppia ew1+ew2 completa in $IMPORT_DIR"

STORICO="$IMPORT_DIR/${TS}_storico_disposizioni.csv"
LOAD_STORICO=0
if [[ -f "$STORICO" ]]; then
  LOAD_STORICO=1
fi

# --- Attendi fine upload (size stabile 2 check da 3s) ---
wait_stable() {
  local f="$1" s1 s2
  s1=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f")
  sleep 3
  s2=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f")
  [[ "$s1" == "$s2" && "$s1" -gt 0 ]] || return 1
  return 0
}

log "Set selezionato: $TS"
log "  EW1=$EW1"
log "  EW2=$EW2"
if [[ "$LOAD_STORICO" -eq 1 ]]; then
  log "  STORICO=$STORICO"
else
  log "  STORICO=assente (skip)"
fi

for f in "$EW1" "$EW2"; do
  wait_stable "$f" || die "file non stabile o vuoto: $f"
done
if [[ "$LOAD_STORICO" -eq 1 ]]; then
  wait_stable "$STORICO" || die "file non stabile o vuoto: $STORICO"
fi

# Header obbligatorio
head -1 "$EW1" | grep -qi 'EW1_ANNO_DISPOSIZIONE' || die "header EW1 inatteso"
head -1 "$EW2" | grep -qi 'EW2_ANNO_DISPOSIZIONE' || die "header EW2 inatteso"

copy_csv() {
  local table="$1" file="$2"
  log "COPY → $table ($(basename "$file"))"
  "${PSQL[@]}" -c "\copy ${table} FROM STDIN WITH (FORMAT csv, HEADER true)" < "$file"
}

log "TRUNCATE…"
if [[ "$LOAD_STORICO" -eq 1 ]]; then
  "${PSQL[@]}" -c "TRUNCATE storico_disposizioni, ew2_righe_disposizioni, ew1_testata_disposizioni;"
else
  "${PSQL[@]}" -c "TRUNCATE ew2_righe_disposizioni, ew1_testata_disposizioni;"
fi

copy_csv ew1_testata_disposizioni "$EW1"
copy_csv ew2_righe_disposizioni "$EW2"
if [[ "$LOAD_STORICO" -eq 1 ]]; then
  copy_csv storico_disposizioni "$STORICO"
fi

log "Conteggi post-import:"
"${PSQL[@]}" -c "
SELECT 'ew1_testata_disposizioni' AS tabella, COUNT(*) AS n FROM ew1_testata_disposizioni
UNION ALL
SELECT 'ew2_righe_disposizioni', COUNT(*) FROM ew2_righe_disposizioni
UNION ALL
SELECT 'storico_disposizioni', COUNT(*) FROM storico_disposizioni
ORDER BY 1;
"

log "Import completato (timestamp=$TS)"
