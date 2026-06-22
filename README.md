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

---

## 3. Database Backups

To prevent data loss, you can dump the current TimescaleDB cache directly into a SQL file on your host machine.

### Create Backup
Run this command from your host terminal to save the database to a compressed file:
```bash
docker exec -t intexdata pg_dump -U postgres postgres | gzip > backup.sql.gz
```

### Restore Backup
To restore the compressed SQL backup back to the database:
```bash
gunzip -c backup.sql.gz | docker exec -i intexdata psql -U postgres -d postgres
```
