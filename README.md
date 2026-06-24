# Intex Consultazione - ERP Dashboard & Cache Layer

This project provides a high-performance local caching dashboard for Intex ERP documents. It caches slow remote Oracle REST Data Services (ORDS) endpoints into a local TimescaleDB/PostgreSQL instance, enabling sub-millisecond querying on the frontend.

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

A synchronization script (`oracle-sync.py`) runs inside the `intex-api` backend container to pull records from the remote Oracle REST server and upsert them into the local TimescaleDB cache.

### 2.1. Incremental Sync (Recommended for regular updates)
Incremental mode only fetches records created or modified since the beginning of the current year. This reduces network payload sizes and speeds up the execution significantly.

To run an incremental sync, execute the following command from your host terminal:
```bash
docker exec -it intex-api python /app/oracle-sync.py --mode incremental
```

### 2.2. Syncing with a Custom Date Range
When date filtering is active (incremental mode, or whenever `--start-date` is set), records are fetched within a date window. Use `--start-date` and optionally `--end-date`, both in `YYYY-MM-DD` format.

- **`--start-date`**: fetch records from this date onward. In incremental mode without `--start-date`, the default start is January 1 of the current year.
- **`--end-date`**: fetch records up to and including this date. If omitted, it defaults to **today**.

Examples:

```bash
# Incremental sync from Jan 1 through today (default end date)
docker exec -it intex-api python /app/oracle-sync.py --mode incremental

# Sync from a specific start date through today
docker exec -it intex-api python /app/oracle-sync.py --start-date 2026-01-01

# Sync an explicit date range
docker exec -it intex-api python /app/oracle-sync.py --start-date 2026-01-01 --end-date 2026-03-31
```

> [!NOTE]
> Querying the remote server using date filters (`--start-date` / `--end-date`) triggers a full table scan on the unindexed remote Oracle view. This operation can take between **20 to 50 seconds** per page. To prevent script failures, the internal HTTP client timeout has been increased to **60 seconds**.

### 2.3. Full Sync (Rebuild Cache)
Full mode pulls the entire historical log from the remote views page-by-page. Use this during initial setup or weekly maintenance.
```bash
docker exec -it intex-api python /app/oracle-sync.py --mode full
```

### 2.4. Batch Size Limit Tuning
If the remote Oracle server is under heavy load or if pagination takes too long and encounters a gateway/read timeout, you can lower the page batch size (default is 100) using the `--limit` parameter (e.g., to 50 or 20). This reduces the query execution time of each page on the Oracle database:
```bash
docker exec -it intex-api python /app/oracle-sync.py --start-date 2026-01-01 --end-date 2026-03-31 --limit 50
```

### 2.5. Selective Sync (`--only`)
By default, the script syncs all five data sets. Use `--only` to run a subset:

| Target | Data synced |
|--------|-------------|
| `clienti` | Customers |
| `articoli` | Articles |
| `fatture` | Invoices and seasons |
| `bolle` | Delivery notes (DDTs) |
| `offerte` | Offers |

Examples:

```bash
# Sync only delivery notes (bolle) for calendar year 2026
docker exec -it intex-api python /app/oracle-sync.py \
  --only bolle \
  --start-date 2026-01-01 \
  --end-date 2026-12-31

# Incremental sync of invoices and offers only
docker exec -it intex-api python /app/oracle-sync.py --mode incremental --only fatture offerte

# Full sync of customers and articles only
docker exec -it intex-api python /app/oracle-sync.py --mode full --only clienti articoli
```

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
