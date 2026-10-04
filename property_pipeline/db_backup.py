"""SQLite snapshots before destructive pipeline operations."""

from __future__ import annotations

import re
import shutil
import sqlite3
import time
from pathlib import Path

from .config import BACKUP_DIR, BACKUP_KEEP, DB_PATH, LEARNED_RULES_PATH


class MonthAlreadyImported(Exception):
    """Raised when run_month would wipe an existing month unless yes=True."""

    def __init__(self, month_str: str, counts: dict[str, int]):
        self.month_str = month_str
        self.counts = counts
        n_tx = counts.get("n_tx", 0)
        n_reviewed = counts.get("n_reviewed", 0)
        super().__init__(
            f"{month_str} already has {n_tx} transactions "
            f"({n_reviewed} marked reviewed). Re-run would wipe those labels."
        )


def _safe_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "", value) or "x"


def month_import_counts(month_str: str, db_path: Path | str | None = None) -> dict[str, int]:
    """Counts for a month already in the DB. Zeros if the DB or tables are missing."""
    path = Path(db_path or DB_PATH)
    empty = {"n_tx": 0, "n_reviewed": 0, "n_needs_review": 0}
    if not path.exists():
        return empty
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "transactions_canonical" not in tables:
            return empty
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS n_tx,
              COALESCE(SUM(CASE WHEN l.reviewed = 1 THEN 1 ELSE 0 END), 0) AS n_reviewed,
              COALESCE(SUM(CASE WHEN l.needs_review = 1 THEN 1 ELSE 0 END), 0) AS n_needs_review
            FROM transactions_canonical c
            LEFT JOIN (
              SELECT l.tx_id, l.reviewed, l.needs_review
              FROM transactions_labels l
              INNER JOIN (
                SELECT tx_id, MAX(label_version) AS mv
                FROM transactions_labels
                GROUP BY tx_id
              ) m ON l.tx_id = m.tx_id AND l.label_version = m.mv
            ) l ON l.tx_id = c.tx_id
            WHERE c.import_batch_id = ? AND c.is_superseded = 0
            """,
            (month_str,),
        ).fetchone()
        return {
            "n_tx": int(row["n_tx"] or 0),
            "n_reviewed": int(row["n_reviewed"] or 0),
            "n_needs_review": int(row["n_needs_review"] or 0),
        }
    except sqlite3.Error:
        return empty
    finally:
        conn.close()


def snapshot_db(
    db_path: Path | str | None = None,
    *,
    reason: str = "snapshot",
    month_str: str | None = None,
    keep: int | None = None,
) -> Path | None:
    """Write a consistent copy of labels.db (VACUUM INTO) plus learned_rules.json.

    Returns the snapshot path, or None if there is no database file yet.
    """
    src = Path(db_path or DB_PATH)
    if not src.exists():
        return None

    dest_dir = BACKUP_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    timestr = time.strftime("%Y%m%d-%H%M%S")
    parts = ["labels", _safe_token(reason)]
    if month_str:
        parts.append(_safe_token(month_str))
    parts.append(timestr)
    dest = dest_dir / ("_".join(parts) + ".db")

    if dest.exists():
        dest.unlink()
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    rules = LEARNED_RULES_PATH
    if rules.exists():
        shutil.copy2(rules, dest.with_suffix(".learned_rules.json"))

    _prune_snapshots(dest_dir, keep if keep is not None else BACKUP_KEEP)
    return dest


def _prune_snapshots(dest_dir: Path, keep: int) -> None:
    if keep < 1:
        return
    dbs = sorted(dest_dir.glob("labels_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for extra in dbs[keep:]:
        extra.unlink(missing_ok=True)
        extra.with_suffix(".learned_rules.json").unlink(missing_ok=True)
