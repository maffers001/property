"""SQLite database schema and connection management."""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS raw_import_rows (
    raw_row_id      TEXT PRIMARY KEY,
    import_batch_id TEXT NOT NULL,
    source_bank     TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    row_number      INTEGER NOT NULL,
    raw_json        TEXT NOT NULL,
    imported_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE TABLE IF NOT EXISTS transactions_canonical (
    tx_id                 TEXT PRIMARY KEY,
    raw_row_id            TEXT,
    import_batch_id       TEXT NOT NULL,
    source_bank           TEXT NOT NULL,
    source_account        TEXT NOT NULL,
    posted_date           TEXT NOT NULL,
    amount                REAL NOT NULL,
    currency              TEXT NOT NULL DEFAULT 'GBP',
    counterparty          TEXT,
    reference             TEXT,
    memo                  TEXT,
    type                  TEXT,
    balance               REAL,
    bank_txn_number       TEXT,
    bank_category         TEXT,
    bank_subcategory      TEXT,
    effective_subcategory TEXT,
    match_text            TEXT,
    description           TEXT,
    parent_tx_id          TEXT,
    is_superseded         INTEGER NOT NULL DEFAULT 0,
    created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    FOREIGN KEY (raw_row_id) REFERENCES raw_import_rows(raw_row_id)
);

CREATE TABLE IF NOT EXISTS transactions_labels (
    tx_id            TEXT NOT NULL,
    label_version    INTEGER NOT NULL,
    property_code    TEXT,
    category         TEXT,
    subcategory      TEXT,
    source           TEXT NOT NULL DEFAULT 'rule',
    confidence       REAL,
    rule_id          TEXT,
    rule_strength    TEXT,
    needs_review     INTEGER NOT NULL DEFAULT 0,
    reviewed         INTEGER NOT NULL DEFAULT 0,
    reviewed_at      TEXT,
    pipeline_version TEXT,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    PRIMARY KEY (tx_id, label_version),
    FOREIGN KEY (tx_id) REFERENCES transactions_canonical(tx_id)
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id         TEXT PRIMARY KEY,
    order_index     INTEGER NOT NULL,
    phase           TEXT NOT NULL,
    pattern         TEXT NOT NULL,
    outputs_json    TEXT NOT NULL,
    strength        TEXT NOT NULL DEFAULT 'strong',
    apply_when_json TEXT,
    banks_json      TEXT,
    accounts_json   TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rule_performance (
    rule_id          TEXT PRIMARY KEY,
    n_matches        INTEGER NOT NULL DEFAULT 0,
    acc_category     REAL,
    acc_subcategory  REAL,
    acc_property     REAL,
    last_computed_at TEXT,
    FOREIGN KEY (rule_id) REFERENCES rules(rule_id)
);

CREATE TABLE IF NOT EXISTS properties (
    property_code   TEXT PRIMARY KEY,
    property_id     INTEGER,
    address         TEXT,
    block           TEXT,
    freehold_entity TEXT
);

CREATE TABLE IF NOT EXISTS tenancies (
    tenancy_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    property_code TEXT NOT NULL,
    tenant_name   TEXT NOT NULL,
    start_date    TEXT NOT NULL,
    end_date      TEXT,
    monthly_rent  REAL,
    FOREIGN KEY (property_code) REFERENCES properties(property_code)
);

CREATE TABLE IF NOT EXISTS merchant_alias (
    alias_pattern      TEXT PRIMARY KEY,
    canonical_merchant TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_canonical_batch ON transactions_canonical(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_canonical_date ON transactions_canonical(posted_date);
CREATE INDEX IF NOT EXISTS idx_labels_txid ON transactions_labels(tx_id);
CREATE INDEX IF NOT EXISTS idx_rules_phase ON rules(phase, order_index);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode enabled."""
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(db_path: Path | str | None = None):
    """Context manager yielding a database connection."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Create all tables if they don't exist."""
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
