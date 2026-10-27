#!/usr/bin/env bash
# Import giornaliero EW1/EW2 (+ opz. storico_disposizioni + opz. c37 + opz. cicli) da CSV SFTP
# → TRUNCATE + \copy nel container Timescale.
#
# Atteso dopo l'export Windows (extract_upload_tables_storico*.py → SFTP):
#   /var/data_imports/intex/{timestamp}_ew1_testata_disposizioni.csv
#   /var/data_imports/intex/{timestamp}_ew2_righe_disposizioni.csv
#   /var/data_imports/intex/{timestamp}_storico_disposizioni.csv   (opzionale)
#   /var/data_imports/intex/{timestamp}_c37_testata_listini.csv   (opzionale, Cod. Univoco)
#   /var/data_imports/intex/{timestamp}_z09_cicli_testate.csv     (opz. → set cicli)
#   /var/data_imports/intex/{timestamp}_z08_cicli_fasi.csv
#   /var/data_imports/intex/{timestamp}_z02_fasi.csv
#   /var/data_imports/intex/{timestamp}_r07_clienti.csv
#   /var/data_imports/intex/{timestamp}_z11_stagioni.csv
#   /var/data_imports/intex/{timestamp}_cw4_composizioni.csv
#   /var/data_imports/intex/{timestamp}_cwa_articoli_cliente.csv
#   /var/data_imports/intex/{timestamp}_cw0_linee.csv
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

C37="$IMPORT_DIR/${TS}_c37_testata_listini.csv"
LOAD_C37=0
if [[ -f "$C37" ]]; then
  LOAD_C37=1
fi

# Cicli: se c'è z09, richiedi l'intero set (stesso timestamp)
CICLI_Z09="$IMPORT_DIR/${TS}_z09_cicli_testate.csv"
CICLI_Z08="$IMPORT_DIR/${TS}_z08_cicli_fasi.csv"
CICLI_Z02="$IMPORT_DIR/${TS}_z02_fasi.csv"
CICLI_R07="$IMPORT_DIR/${TS}_r07_clienti.csv"
CICLI_Z11="$IMPORT_DIR/${TS}_z11_stagioni.csv"
CICLI_CW4="$IMPORT_DIR/${TS}_cw4_composizioni.csv"
CICLI_CWA="$IMPORT_DIR/${TS}_cwa_articoli_cliente.csv"
CICLI_CW0="$IMPORT_DIR/${TS}_cw0_linee.csv"
LOAD_CICLI=0
if [[ -f "$CICLI_Z09" ]]; then
  LOAD_CICLI=1
  for f in "$CICLI_Z08" "$CICLI_Z02" "$CICLI_R07" "$CICLI_Z11" "$CICLI_CW4" "$CICLI_CWA" "$CICLI_CW0"; do
    [[ -f "$f" ]] || die "set cicli incompleto (manca $(basename "$f")) per timestamp=$TS"
  done
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
if [[ "$LOAD_C37" -eq 1 ]]; then
  log "  C37=$C37"
else
  log "  C37=assente (skip)"
fi
if [[ "$LOAD_CICLI" -eq 1 ]]; then
  log "  CICLI=z09+z08+z02+r07+z11+cw4+cwa+cw0"
else
  log "  CICLI=assente (skip)"
fi

for f in "$EW1" "$EW2"; do
  wait_stable "$f" || die "file non stabile o vuoto: $f"
done
if [[ "$LOAD_STORICO" -eq 1 ]]; then
  wait_stable "$STORICO" || die "file non stabile o vuoto: $STORICO"
fi
if [[ "$LOAD_C37" -eq 1 ]]; then
  wait_stable "$C37" || die "file non stabile o vuoto: $C37"
fi
if [[ "$LOAD_CICLI" -eq 1 ]]; then
  for f in "$CICLI_Z09" "$CICLI_Z08" "$CICLI_Z02" "$CICLI_R07" "$CICLI_Z11" "$CICLI_CW4" "$CICLI_CWA" "$CICLI_CW0"; do
    wait_stable "$f" || die "file non stabile o vuoto: $f"
  done
fi

# Header obbligatorio
head -1 "$EW1" | grep -qi 'EW1_ANNO_DISPOSIZIONE' || die "header EW1 inatteso"
head -1 "$EW2" | grep -qi 'EW2_ANNO_DISPOSIZIONE' || die "header EW2 inatteso"
if [[ "$LOAD_C37" -eq 1 ]]; then
  head -1 "$C37" | grep -qi 'c37_prg' || die "header c37 inatteso (manca c37_prg)"
fi
if [[ "$LOAD_CICLI" -eq 1 ]]; then
  head -1 "$CICLI_Z09" | grep -qi 'codice_ciclo' || die "header z09 cicli inatteso"
  head -1 "$CICLI_Z08" | grep -qi 'sequenza' || die "header z08 cicli inatteso"
fi

copy_csv() {
  local table="$1" file="$2"
  log "COPY → $table ($(basename "$file"))"
  "${PSQL[@]}" -c "\copy ${table} FROM STDIN WITH (FORMAT csv, HEADER true)" < "$file"
}

log "TRUNCATE storico…"
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

if [[ "$LOAD_C37" -eq 1 ]]; then
  log "TRUNCATE c37_testata_listini…"
  "${PSQL[@]}" -c "TRUNCATE c37_testata_listini;"
  copy_csv c37_testata_listini "$C37"
fi

if [[ "$LOAD_CICLI" -eq 1 ]]; then
  log "TRUNCATE cicli…"
  # Nessuna FK tra queste tabelle; cicli_search va svuotata prima del refresh
  "${PSQL[@]}" -c "
    TRUNCATE cicli_search,
             cicli_fasi,
             cicli_testate,
             fasi_lavoro,
             cicli_clienti,
             cicli_stagioni,
             composizioni,
             articoli_cliente,
             linee_tintoria;
  "

  # Anagrafiche prima, poi testate/fasi
  copy_csv fasi_lavoro "$CICLI_Z02"
  copy_csv cicli_clienti "$CICLI_R07"
  copy_csv cicli_stagioni "$CICLI_Z11"
  copy_csv composizioni "$CICLI_CW4"
  copy_csv articoli_cliente "$CICLI_CWA"
  copy_csv linee_tintoria "$CICLI_CW0"
  copy_csv cicli_testate "$CICLI_Z09"
  copy_csv cicli_fasi "$CICLI_Z08"

  log "refresh_cicli_search…"
  "${PSQL[@]}" -c "SELECT public.refresh_cicli_search() AS cicli_search_rows;"
fi

log "Conteggi post-import:"
"${PSQL[@]}" -c "
SELECT 'ew1_testata_disposizioni' AS tabella, COUNT(*) AS n FROM ew1_testata_disposizioni
UNION ALL SELECT 'ew2_righe_disposizioni', COUNT(*) FROM ew2_righe_disposizioni
UNION ALL SELECT 'storico_disposizioni', COUNT(*) FROM storico_disposizioni
UNION ALL SELECT 'c37_testata_listini', COUNT(*) FROM c37_testata_listini
UNION ALL SELECT 'cicli_testate', COUNT(*) FROM cicli_testate
UNION ALL SELECT 'cicli_fasi', COUNT(*) FROM cicli_fasi
UNION ALL SELECT 'fasi_lavoro', COUNT(*) FROM fasi_lavoro
UNION ALL SELECT 'cicli_clienti', COUNT(*) FROM cicli_clienti
UNION ALL SELECT 'cicli_stagioni', COUNT(*) FROM cicli_stagioni
UNION ALL SELECT 'composizioni', COUNT(*) FROM composizioni
UNION ALL SELECT 'articoli_cliente', COUNT(*) FROM articoli_cliente
UNION ALL SELECT 'linee_tintoria', COUNT(*) FROM linee_tintoria
UNION ALL SELECT 'cicli_search', COUNT(*) FROM cicli_search
ORDER BY 1;
"

log "Import completato (timestamp=$TS, storico=$LOAD_STORICO, c37=$LOAD_C37, cicli=$LOAD_CICLI)"
