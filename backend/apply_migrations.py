#!/usr/bin/env python3
"""
Apply SQL migrations to an existing database (local or production).

Docker init scripts only run on first container creation; use this for DBs
that already exist with transactional data.

Usage:
  python apply_migrations.py                    # apply all pending migrations
  python apply_migrations.py create-analytics.sql
  python apply_migrations.py fatture-composite-pk.sql create-analytics.sql
"""

import argparse
import os
import sys
from pathlib import Path

from database import DatabasePool

_DEFAULT_MIGRATIONS = Path(__file__).resolve().parent.parent / "data" / "migrations"
MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR", str(_DEFAULT_MIGRATIONS)))

DEFAULT_ORDER = [
    "fatture-composite-pk.sql",
    "remove-offerte-stato.sql",
    "create-analytics.sql",
]


def apply_file(cursor, path: Path):
    print(f"Applying {path.name}...")
    sql = path.read_text(encoding="utf-8")
    cursor.execute(sql)
    print(f"  OK: {path.name}")


def main():
    parser = argparse.ArgumentParser(description="Apply SQL migrations to TimescaleDB/PostgreSQL")
    parser.add_argument(
        "files",
        nargs="*",
        help="Migration filenames (default: all known migrations in order)",
    )
    args = parser.parse_args()

    if args.files:
        paths = []
        for name in args.files:
            path = MIGRATIONS_DIR / name
            if not path.is_file():
                print(f"Error: migration not found: {path}", file=sys.stderr)
                sys.exit(1)
            paths.append(path)
    else:
        paths = [MIGRATIONS_DIR / name for name in DEFAULT_ORDER if (MIGRATIONS_DIR / name).is_file()]

    if not paths:
        print("No migration files found.", file=sys.stderr)
        sys.exit(1)

    db_pool = DatabasePool()
    conn = db_pool.get_conn()
    cursor = conn.cursor()
    try:
        for path in paths:
            apply_file(cursor, path)
        conn.commit()
        print("\nMigrations applied successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"\nMigration failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()
        db_pool.release_conn(conn)


if __name__ == "__main__":
    main()
