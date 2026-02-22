#!/usr/bin/env python3
"""Wipe all data from the property pipeline database. Keeps schema; all tables are emptied."""

import sys
from pathlib import Path

# Run from repo root so property_pipeline is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from property_pipeline.config import DB_PATH
from property_pipeline.db import get_db, get_connection


# Tables in dependency order (children first) so FK checks don't block deletes
TABLES = [
    "transactions_labels",
    "transactions_canonical",
    "raw_import_rows",
    "rule_performance",
    "tenancies",
    "rules",
    "properties",
    "merchant_alias",
    "config",
    "custom_list_entries",
]


def main() -> None:
    print(f"Database: {DB_PATH}")
    if not DB_PATH.exists():
        print("Database file does not exist. Nothing to wipe.")
        return

    confirm = input("Wipe all data? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    with get_db(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            for table in TABLES:
                cur = conn.execute(f"DELETE FROM {table}")
                n = cur.rowcount
                if n:
                    print(f"  {table}: deleted {n} row(s)")
        finally:
            conn.execute("PRAGMA foreign_keys=ON")

    # VACUUM must run outside a transaction
    conn = get_connection(DB_PATH)
    conn.isolation_level = None
    conn.execute("VACUUM")
    conn.close()
    print("  VACUUM done.")
    print("Database wiped.")


if __name__ == "__main__":
    main()
