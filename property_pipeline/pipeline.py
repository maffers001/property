"""Main pipeline orchestrator: combines import, rule engine, and export."""

import json
import sqlite3
from pathlib import Path

from .config import (
    BANK_DOWNLOAD_DIR, GENERATED_DIR, CHECKED_DIR, REVIEW_DIR, DB_PATH,
)
from .db import init_db, get_db
from .importers import load_month_files
from .engine import run_engine
from .export import (
    build_output_dataframe, write_xlsx, write_csv,
    write_review_queue, write_diagnostic_ddcheck, write_diagnostic_catcheck,
)
from .rules_seed import get_all_rules, PROPERTIES_SEED


def seed_db(db_path: Path | str | None = None) -> None:
    """Initialise the database and seed rules + properties."""
    db = db_path or DB_PATH
    init_db(db)

    with get_db(db) as conn:
        # Seed properties
        for p in PROPERTIES_SEED:
            conn.execute(
                """INSERT OR REPLACE INTO properties
                   (property_code, property_id, address, block, freehold_entity)
                   VALUES (?, ?, ?, ?, ?)""",
                (p["property_code"], p.get("property_id"), p.get("address"),
                 p.get("block"), p.get("freehold_entity")),
            )

        # Seed rules
        for r in get_all_rules():
            conn.execute(
                """INSERT OR REPLACE INTO rules
                   (rule_id, order_index, phase, pattern, outputs_json,
                    strength, apply_when_json, banks_json, accounts_json, enabled)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r["rule_id"], r["order_index"], r["phase"], r["pattern"],
                 r["outputs_json"], r["strength"], r["apply_when_json"],
                 r["banks_json"], r["accounts_json"], r["enabled"]),
            )

        # Seed default config
        defaults = {
            "confidence_auto_accept": "0.93",
            "confidence_force_review": "0.75",
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (k, v),
            )


def _load_rules_from_db(conn: sqlite3.Connection) -> list[dict]:
    """Load all enabled rules from the database."""
    cursor = conn.execute(
        "SELECT * FROM rules WHERE enabled=1 ORDER BY phase, order_index"
    )
    return [dict(row) for row in cursor.fetchall()]


def _load_properties_set(conn: sqlite3.Connection) -> set[str]:
    """Load valid property codes from the database."""
    cursor = conn.execute("SELECT property_code FROM properties")
    return {row["property_code"] for row in cursor.fetchall()}


def _store_raw_rows(conn: sqlite3.Connection, raw_rows: list[dict]) -> int:
    """Insert raw rows, skipping duplicates. Returns count inserted."""
    inserted = 0
    for r in raw_rows:
        try:
            conn.execute(
                """INSERT INTO raw_import_rows
                   (raw_row_id, import_batch_id, source_bank, source_file,
                    row_number, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (r["raw_row_id"], r["import_batch_id"], r["source_bank"],
                 r["source_file"], r["row_number"], r["raw_json"]),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    return inserted


def _store_canonical_rows(conn: sqlite3.Connection, canonical_rows: list[dict]) -> int:
    """Insert canonical rows, skipping duplicates. Returns count inserted."""
    inserted = 0
    cols = [
        "tx_id", "raw_row_id", "import_batch_id", "source_bank",
        "source_account", "posted_date", "amount", "currency",
        "counterparty", "reference", "memo", "type", "balance",
        "bank_txn_number", "bank_category", "bank_subcategory",
        "effective_subcategory", "match_text", "description",
        "parent_tx_id", "is_superseded",
    ]
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)

    for r in canonical_rows:
        try:
            conn.execute(
                f"INSERT INTO transactions_canonical ({col_names}) VALUES ({placeholders})",
                tuple(r.get(c) for c in cols),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    return inserted


def _store_labels(conn: sqlite3.Connection, labels: list[dict], pipeline_version: str = "0.1.0") -> int:
    """Insert label rows (version 1). Returns count inserted."""
    inserted = 0
    for lab in labels:
        try:
            conn.execute(
                """INSERT INTO transactions_labels
                   (tx_id, label_version, property_code, category, subcategory,
                    source, confidence, rule_id, rule_strength, needs_review,
                    reviewed, pipeline_version)
                   VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (lab["tx_id"], lab.get("property_code"), lab.get("category"),
                 lab.get("subcategory"), lab.get("source", "rule"),
                 lab.get("confidence"), lab.get("rule_id"),
                 lab.get("rule_strength"), lab.get("needs_review", 0),
                 pipeline_version),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    return inserted


def run_month(
    month_str: str,
    bank_download_dir: Path | str | None = None,
    db_path: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> dict:
    """Run the full pipeline for a single month.

    Args:
        month_str: e.g. 'OCT2025'
        bank_download_dir: override for bank CSV folder
        db_path: override for database path
        output_dir: override for output folder (generated/)

    Returns:
        Summary dict with counts.
    """
    bd_dir = Path(bank_download_dir) if bank_download_dir else BANK_DOWNLOAD_DIR
    db = db_path or DB_PATH
    gen_dir = Path(output_dir) if output_dir else GENERATED_DIR

    seed_db(db)

    # 1. Import bank CSVs
    raw_rows, canonical_rows = load_month_files(bd_dir, month_str)
    print(f"Loaded {len(canonical_rows)} transactions for {month_str}")

    with get_db(db) as conn:
        # 2. Store in DB
        n_raw = _store_raw_rows(conn, raw_rows)
        n_canon = _store_canonical_rows(conn, canonical_rows)
        print(f"Stored {n_raw} raw rows, {n_canon} canonical rows (new)")

        # 3. Load rules and properties
        rules = _load_rules_from_db(conn)
        properties_set = _load_properties_set(conn)

    # 4. Run engine
    labels = run_engine(canonical_rows, rules, properties_set)
    print(f"Engine produced {len(labels)} labels")

    with get_db(db) as conn:
        # 5. Store labels
        n_labels = _store_labels(conn, labels)
        print(f"Stored {n_labels} labels")

    # 6. Export
    gen_dir.mkdir(parents=True, exist_ok=True)

    output_df = build_output_dataframe(canonical_rows, labels)

    draft_xlsx = gen_dir / f"{month_str}_codedAndCategorised.xlsx"
    draft_csv = gen_dir / f"{month_str}_codedAndCategorised.csv"
    write_xlsx(output_df, draft_xlsx)
    write_csv(output_df, draft_csv)
    print(f"Draft written: {draft_xlsx}")

    # Review queue
    review_dir = REVIEW_DIR
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"review_queue_{month_str}.xlsx"
    n_review = write_review_queue(canonical_rows, labels, review_path)
    print(f"Review queue: {n_review} items -> {review_path}")

    # Diagnostics
    dd_path = gen_dir / f"DDCheck_{month_str}.csv"
    cat_path = gen_dir / f"CatCheck_{month_str}.csv"
    write_diagnostic_ddcheck(canonical_rows, labels, dd_path)
    write_diagnostic_catcheck(canonical_rows, labels, cat_path)
    print(f"Diagnostics: {dd_path}, {cat_path}")

    return {
        "month": month_str,
        "total_transactions": len(canonical_rows),
        "needs_review": n_review,
        "draft_xlsx": str(draft_xlsx),
        "review_queue": str(review_path),
    }


def finalize_month(
    month_str: str,
    db_path: Path | str | None = None,
    source_dir: Path | str | None = None,
) -> Path:
    """Copy the draft output to checked/ as the final file.

    In a full workflow this would re-read from DB with any manual corrections.
    For now it copies from generated/ to checked/.
    """
    gen_dir = Path(source_dir) if source_dir else GENERATED_DIR
    checked_dir = CHECKED_DIR
    checked_dir.mkdir(parents=True, exist_ok=True)

    source = gen_dir / f"{month_str}_codedAndCategorised.xlsx"
    dest = checked_dir / f"{month_str}_codedAndCategorised.xlsx"

    if not source.exists():
        raise FileNotFoundError(f"Draft not found: {source}")

    import shutil
    shutil.copy2(source, dest)
    print(f"Finalized: {dest}")

    # Also copy CSV
    source_csv = gen_dir / f"{month_str}_codedAndCategorised.csv"
    if source_csv.exists():
        dest_csv = checked_dir / f"{month_str}_codedAndCategorised.csv"
        shutil.copy2(source_csv, dest_csv)

    return dest


def review_month(
    month_str: str,
    db_path: Path | str | None = None,
) -> None:
    """Apply corrections from the review queue file back to the database.

    Reads the review queue XLSX (which the user may have edited) and updates
    transactions_labels with new versions for any changed rows.
    """
    db = db_path or DB_PATH
    review_path = REVIEW_DIR / f"review_queue_{month_str}.xlsx"

    if not review_path.exists():
        print(f"No review queue found at {review_path}")
        return

    import pandas as pd
    df = pd.read_excel(review_path, engine="openpyxl", index_col=0)

    if df.empty:
        print("Review queue is empty.")
        return

    with get_db(db) as conn:
        for _, row in df.iterrows():
            tx_id = row.get("tx_id")
            if not tx_id:
                continue

            # Get current max version
            cur = conn.execute(
                "SELECT MAX(label_version) as mv FROM transactions_labels WHERE tx_id=?",
                (tx_id,),
            )
            max_ver = cur.fetchone()["mv"] or 0
            new_ver = max_ver + 1

            conn.execute(
                """INSERT INTO transactions_labels
                   (tx_id, label_version, property_code, category, subcategory,
                    source, confidence, rule_id, rule_strength, needs_review,
                    reviewed, reviewed_at)
                   VALUES (?, ?, ?, ?, ?, 'manual', 1.0, NULL, NULL, 0, 1,
                           strftime('%Y-%m-%dT%H:%M:%S','now'))""",
                (tx_id, new_ver,
                 row.get("property_code", ""),
                 row.get("category", ""),
                 row.get("subcategory", "")),
            )

    print(f"Applied {len(df)} review corrections for {month_str}")
