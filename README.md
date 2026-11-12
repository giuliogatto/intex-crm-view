# Intex Consultazione - ERP Dashboard & Cache Layer

This project provides a high-performance local caching dashboard for Intex ERP documents. Oracle data is exported to CSV, imported into a local TimescaleDB/PostgreSQL cache, and served to the frontend with sub-millisecond querying.

---

## 1. Running the System

Start the three Docker Compose services in order:

1. **Database & Network**:
   ```bash
   cd data
   docker compose up -d
   ```
2. **Backend Application**:
   ```bash
   cd ../backend
   docker compose up -d
   ```
3. **Frontend Application**:
   ```bash
   cd ../frontend
   docker compose up -d
   ```

The dashboard will be accessible on your host machine at **[http://localhost:5447](http://localhost:5447)**.

---

## 2. Synchronizing Data from Oracle

Data sync uses a two-step pipeline: export from Oracle to CSV over SFTP, then import into TimescaleDB.

1. **`scripts/extract_upload_tables_storico_365.py`** — connects directly to Oracle, exports CSV files, and uploads them via SFTP to `/var/data_imports/intex/` on the Debian host.
2. **`scripts/import_storico_disposizioni.sh`** — on the server, loads the latest matching CSV set into TimescaleDB (`TRUNCATE` + `\copy`).

> [!NOTE]
> `backend/oracle-sync.py` (ORDS REST sync inside `intex-api`) is **obsolete**. It remains in the repo for reference only; do not use it to keep the cache up to date.

### 2.1. Export + upload (Windows / Oracle side)

Run the extract script where it can reach Oracle and the SFTP host (typically a scheduled Windows task):

```bash
python scripts/extract_upload_tables_storico_365.py
```

Default window: `LOOKBACK_DAYS = 365` on bolla cliente / DDT uscita dates. Set `LOOKBACK_DAYS = None` for a full dump (much larger files). Anagrafica cicli and C37 offerte are always exported in full.

| Flag / area | CSV produced (prefix `{timestamp}_`) |
|-------------|--------------------------------------|
| Storico disposizioni | `ew1_testata_disposizioni`, `ew2_righe_disposizioni`, `storico_disposizioni` |
| Offerte (C37) | `c37_testata_listini` |
| DDT uscita (`EXPORT_DDT`) | `ddt_testate`, `ddt_righe`, `clienti_anagrafica` |
| Prezzi mancanti (`EXPORT_DDT_PREZZI_003W`) | `ddt_prezzi_003w` |
| Cicli (`EXPORT_CICLI`) | `z09_cicli_testate`, `z08_cicli_fasi`, `z02_fasi`, `r07_clienti`, `z11_stagioni`, `cw4_composizioni`, `cwa_articoli_cliente`, `cw0_linee` |

### 2.2. Import into TimescaleDB (Debian side)

After the CSV files land under `/var/data_imports/intex/`:

```bash
./scripts/import_storico_disposizioni.sh
```

Optional overrides: `IMPORT_DIR=/path/to/csv` and `CONTAINER=<timescale-container-name>`.

The importer picks the newest complete EW1+EW2 timestamp pair and loads optional sets (storico, C37, DDT, prezzi 003W, cicli) when present for that same timestamp.

### 2.3. Analytics layer (materialized views)

The `analytics` schema (fatturato mensile, snapshot clienti, lead time, anomalie) is independent of the CSV pipeline. Apply the migration once on an existing volume, then refresh manually when needed.

```bash
cd backend
python apply_migrations.py create-analytics.sql
```

Or from the API container:

```bash
docker exec -it intex-api python /app/apply_migrations.py create-analytics.sql
```

Refresh aggregates:

```bash
docker exec -it intex-api python -c "from analytics import refresh_analytics_layer; from database import DatabasePool; refresh_analytics_layer(DatabasePool())"
```

Open the **Analisi** dashboard at [http://localhost:5447/analisi](http://localhost:5447/analisi).

---

## 3. Database Backups

To prevent data loss, dump the TimescaleDB cache to a compressed SQL file on your host machine. Use these commands to copy data between environments (e.g. development → production).

### 3.1. Create Backup

Run from the repository root. The dump excludes TimescaleDB internal schemas (not used by this app) so restores work across different TimescaleDB versions.

```bash
cd data
docker compose exec -T timescaledb-intex pg_dump -U postgres \
  --exclude-schema=_timescaledb_catalog \
  --exclude-schema=_timescaledb_config \
  --exclude-schema=_timescaledb_internal \
  postgres 2>/dev/null | gzip > ../backup.sql.gz
```

> [!IMPORTANT]
> Do **not** use `-t` / `-it` on `pg_dump`. A TTY causes `pg_dump` warnings to be written into the SQL file and corrupts the backup.

Verify the backup before copying it anywhere:

```bash
ls -lh ../backup.sql.gz          # expect ~1–2 MB with a populated cache
gunzip -c ../backup.sql.gz | head -5   # should start with "-- PostgreSQL database dump"
gunzip -c ../backup.sql.gz | wc -l     # expect ~140000+ lines
```

To copy to a remote server:

```bash
scp ../backup.sql.gz user@production-host:/opt/intex/intex-crm-view/
```

### 3.2. Restore Backup

A restore **replaces the entire database**. Stop the backend first, recreate an empty `postgres` database, then load the dump with foreign-key checks disabled.

```bash
# 1. Stop the API so it releases DB connections
cd backend
docker compose stop

# 2. Recreate an empty database (connect via template1 — you cannot drop the DB you are connected to)
cd ../data
docker compose exec -T timescaledb-intex psql -U postgres -d template1 <<'EOF'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'postgres' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS postgres;
CREATE DATABASE postgres;
EOF

# 3. Restore (adjust the path to your backup file)
cd ..
(
  echo "SET session_replication_role = replica;"
  gunzip -c backup.sql.gz | grep -v '^pg_dump:' | awk '
{ gsub(/\r$/, "") }
/^COPY _timescaledb/ { skip=1; next }
skip && /^\\.$/ { skip=0; next }
skip { next }
/SELECT pg_catalog.setval/ && /_timescaledb/ { next }
{ print }
'
  echo "SET session_replication_role = DEFAULT;"
) | docker compose -f data/docker-compose.yml exec -T timescaledb-intex \
    psql -U postgres -d postgres -v ON_ERROR_STOP=1

# 4. Verify row counts
docker compose -f data/docker-compose.yml exec -T timescaledb-intex psql -U postgres -d postgres -c "
SELECT 'stagioni' AS t, count(*) FROM stagioni
UNION ALL SELECT 'fatture_testate', count(*) FROM fatture_testate
UNION ALL SELECT 'fatture_righe', count(*) FROM fatture_righe
UNION ALL SELECT 'ddt_testate', count(*) FROM ddt_testate
UNION ALL SELECT 'ddt_righe', count(*) FROM ddt_righe;
"

# 5. Restart the API
cd backend
docker compose up -d
```

The `awk` step strips any TimescaleDB catalog `COPY` blocks that may still be present in older backups. `session_replication_role = replica` disables foreign-key checks during load so parent/child tables can be restored in any order.

You should see many `COPY` lines with large counts (e.g. `COPY 1799`, `COPY 4765`). If the restore prints only a few `SET` lines, the backup file is empty or corrupt — re-create it using the commands in §3.1 and check `ls -lh` before uploading.
