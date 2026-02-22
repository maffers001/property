"""Bulk load historical XLSX ground truth into the DB and rule grading."""

import sqlite3
from pathlib import Path

import pandas as pd

from .config import BANK_DOWNLOAD_DIR, CHECKED_DIR, DB_PATH
from .db import get_db, init_db
from .importers import load_month_files
from .backtest import load_ground_truth
from .engine import run_engine
from .rules_seed import get_all_rules, PROPERTIES_SEED
from .pipeline import seed_db, _store_raw_rows, _store_canonical_rows, _load_rules_from_db, _load_properties_set  # noqa: F401


def _match_keys(truth: pd.DataFrame, canonical_rows: list[dict]) -> list[tuple[str, str, str, str]]:
    """Build (tx_id, property_code, category, subcategory) for each canonical row that matches truth.
    Match on (posted_date, source_account, amount, memo) -> truth (Date, Account, Amount, Memo).
    Returns list of (tx_id, Property, Cat, Subcat) from truth for matched canonical rows.
    """
    truth = truth.copy()
    truth["Amount"] = pd.to_numeric(truth["Amount"], errors="coerce").fillna(0)
    for col in ["Property", "Cat", "Subcat"]:
        truth[col] = truth[col].astype(str).str.strip()
        truth.loc[truth[col].isin(["nan", "None", ""]), col] = ""
    truth["Account"] = truth["Account"].astype(str).str.strip()
    truth["Memo"] = truth["Memo"].astype(str).str.strip()
    truth["_date_str"] = truth.index.strftime("%Y-%m-%d") if hasattr(truth.index, "strftime") else truth.index.astype(str)
    truth["_key"] = truth["_date_str"] + "|" + truth["Account"] + "|" + truth["Amount"].round(2).astype(str) + "|" + truth["Memo"]

    key_to_truth = {}
    for idx, row in truth.iterrows():
        key_to_truth[row["_key"]] = (row["Property"], row["Cat"], row["Subcat"])

    results = []
    for r in canonical_rows:
        if r.get("is_superseded"):
            continue
        date_str = r["posted_date"]
        acc = r.get("source_account") or ""
        amount = r.get("amount")
        memo = r.get("memo") or ""
        try:
            amt_str = f"{float(amount):.2f}"
        except (TypeError, ValueError):
            amt_str = str(amount)
        key = f"{date_str}|{acc}|{amt_str}|{memo}"
        if key in key_to_truth:
            prop, cat, subcat = key_to_truth[key]
            results.append((r["tx_id"], prop, cat, subcat))
    return results


def _next_label_version(conn: sqlite3.Connection, tx_id: str) -> int:
    cur = conn.execute("SELECT MAX(label_version) AS mv FROM transactions_labels WHERE tx_id = ?", (tx_id,))
    row = cur.fetchone()
    return (row["mv"] or 0) + 1


def load_historical_into_db(
    months: list[str] | None = None,
    bank_download_dir: Path | str | None = None,
    checked_dir: Path | str | None = None,
    db_path: Path | str | None = None,
) -> dict:
    """Load historical XLSX ground truth into the DB.

    For each month with both bank CSVs and a checked XLSX: import bank -> canonical,
    store raw + canonical, load XLSX, match rows, insert manual labels (source=manual, reviewed=1).
    """
    bd = Path(bank_download_dir) if bank_download_dir else BANK_DOWNLOAD_DIR
    cd = Path(checked_dir) if checked_dir else CHECKED_DIR
    db = db_path or DB_PATH

    seed_db(db)
    init_db(db)

    if months is None:
        months = []
        for f in sorted(cd.glob("*_codedAndCategorised.xlsx")):
            m = f.name.replace("_codedAndCategorised.xlsx", "")
            months.append(m)

    total_canonical = 0
    total_labels = 0
    by_month = {}

    with get_db(db) as conn:
        for month_str in months:
            truth = load_ground_truth(month_str, cd)
            if truth is None:
                continue
            try:
                raw_rows, canonical_rows = load_month_files(bd, month_str)
            except Exception as e:
                print(f"  {month_str}: skip (bank files: {e})")
                continue
            if not canonical_rows:
                continue

            n_raw = _store_raw_rows(conn, raw_rows)
            n_canon = _store_canonical_rows(conn, canonical_rows)
            total_canonical += n_canon

            matched = _match_keys(truth, canonical_rows)
            inserted = 0
            for tx_id, prop, cat, subcat in matched:
                ver = _next_label_version(conn, tx_id)
                try:
                    conn.execute(
                        """INSERT INTO transactions_labels
                           (tx_id, label_version, property_code, category, subcategory,
                            source, confidence, rule_id, rule_strength, needs_review,
                            reviewed, reviewed_at)
                           VALUES (?, ?, ?, ?, ?, 'manual', 1.0, NULL, NULL, 0, 1,
                                   strftime('%Y-%m-%dT%H:%M:%S','now'))""",
                        (tx_id, ver, prop, cat, subcat),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    pass
            total_labels += inserted
            by_month[month_str] = {"canonical": n_canon, "labels": inserted}
            print(f"  {month_str}: {n_canon} canonical, {inserted} manual labels")

    return {"total_canonical": total_canonical, "total_labels": total_labels, "by_month": by_month}


def grade_rules(db_path: Path | str | None = None) -> dict:
    """Run rule engine over canonical rows that have manual labels; fill rule_performance."""
    db = db_path or DB_PATH

    with get_db(db) as conn:
        # All canonical rows that have at least one label (we'll use latest label as truth)
        cur = conn.execute("""
            SELECT c.* FROM transactions_canonical c
            INNER JOIN (
                SELECT tx_id, MAX(label_version) AS mv FROM transactions_labels
                GROUP BY tx_id
            ) l ON c.tx_id = l.tx_id
            WHERE c.is_superseded = 0
        """)
        canonical_rows = [dict(row) for row in cur.fetchall()]

        if not canonical_rows:
            print("No canonical rows with labels in DB. Run load_historical first.")
            return {"rules_graded": 0}

        # Latest label per tx_id (manual preferred for grading)
        cur = conn.execute("""
            SELECT tx_id, property_code, category, subcategory
            FROM transactions_labels l1
            WHERE label_version = (
                SELECT MAX(label_version) FROM transactions_labels l2 WHERE l2.tx_id = l1.tx_id
            )
        """)
        manual_by_tx = {row["tx_id"]: dict(row) for row in cur.fetchall()}

        rules = _load_rules_from_db(conn)
        properties_set = _load_properties_set(conn)
    if not rules:
        rules = get_all_rules()
    if not properties_set:
        properties_set = {p["property_code"] for p in PROPERTIES_SEED}
    predicted = run_engine(canonical_rows, rules, properties_set)

    # predicted has tx_id, property_code, category, subcategory, rule_id
    # Compare to manual_by_tx; aggregate by rule_id
    from collections import defaultdict
    by_rule = defaultdict(lambda: {"n": 0, "cat_ok": 0, "subcat_ok": 0, "prop_ok": 0})

    for lab in predicted:
        tx_id = lab["tx_id"]
        if tx_id not in manual_by_tx:
            continue
        manual = manual_by_tx[tx_id]
        rule_id = lab.get("rule_id") or "unknown"
        by_rule[rule_id]["n"] += 1
        if manual.get("category") == lab.get("category"):
            by_rule[rule_id]["cat_ok"] += 1
        if manual.get("subcategory") == lab.get("subcategory"):
            by_rule[rule_id]["subcat_ok"] += 1
        if manual.get("property_code") == lab.get("property_code"):
            by_rule[rule_id]["prop_ok"] += 1

    from datetime import datetime
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    valid_rule_ids = {r["rule_id"] for r in rules}

    with get_db(db) as conn:
        inserted = 0
        for rule_id, counts in by_rule.items():
            if rule_id not in valid_rule_ids:
                continue
            n = counts["n"]
            if n == 0:
                continue
            acc_cat = counts["cat_ok"] / n
            acc_sub = counts["subcat_ok"] / n
            acc_prop = counts["prop_ok"] / n
            conn.execute(
                """INSERT OR REPLACE INTO rule_performance
                   (rule_id, n_matches, acc_category, acc_subcategory, acc_property, last_computed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (rule_id, n, acc_cat, acc_sub, acc_prop, now),
            )
            inserted += 1
        print(f"Graded {inserted} rules")

    return {"rules_graded": inserted}
