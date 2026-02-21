"""CSV importers for Barclays and Starling bank files."""

import hashlib
import json
import uuid
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import STARLING_ACCOUNT


def _compute_tx_id(
    source_bank: str,
    source_account: str,
    posted_date: str,
    amount: float,
    counterparty: str,
    reference: str,
    memo: str,
    bank_txn_number: str,
    row_number: int,
) -> str:
    parts = [
        source_bank,
        source_account,
        posted_date,
        str(amount),
        counterparty or "",
        reference or "",
        memo or "",
        bank_txn_number or "",
        str(row_number),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_match_text(counterparty: str | None, reference: str | None, memo: str | None, txn_type: str | None) -> str:
    parts = [p for p in [counterparty, reference, memo, txn_type] if p]
    return " ".join(parts).strip()


def load_barclays(filepath: str | Path, import_batch_id: str) -> tuple[list[dict], list[dict]]:
    """Load a Barclays CSV and return (raw_rows, canonical_rows)."""
    filepath = Path(filepath)
    source_file = filepath.name

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.ParserWarning)
        try:
            df = pd.read_csv(
                filepath,
                names=["Number", "Date", "Account", "Amount", "Subcategory", "Memo"],
                skiprows=1,
                dtype=str,
                on_bad_lines="warn",
            )
        except (TypeError, Exception):
            df = None
    if df is None:
        # Variable columns (e.g. extra comma in Memo) - use python engine, take first 6
        try:
            df = pd.read_csv(filepath, skiprows=1, dtype=str, engine="python", on_bad_lines="warn")
        except TypeError:
            df = pd.read_csv(filepath, skiprows=1, dtype=str, engine="python")
        ncol = min(6, df.shape[1])
        df = df.iloc[:, :ncol].copy()
        df.columns = ["Number", "Date", "Account", "Amount", "Subcategory", "Memo"][:ncol]
        for c in ["Number", "Date", "Account", "Amount", "Subcategory", "Memo"]:
            if c not in df.columns:
                df[c] = ""
    if "Memo2" not in df.columns:
        df["Memo2"] = ""
    for c in ["Number", "Date", "Account", "Amount", "Subcategory", "Memo"]:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("")
    df = df.fillna("")
    df = df.replace("\t", "", regex=True)

    raw_rows = []
    canonical_rows = []

    for idx, row in df.iterrows():
        try:
            row_number = int(idx) + 1
        except (TypeError, ValueError):
            row_number = 1
        raw_row_id = f"{import_batch_id}_{source_file}_{row_number}"

        raw_dict = {k: str(row[k]) if pd.notna(row[k]) else "" for k in df.columns}
        raw_rows.append({
            "raw_row_id": raw_row_id,
            "import_batch_id": str(import_batch_id),
            "source_bank": "barclays",
            "source_file": str(source_file),
            "row_number": row_number,
            "raw_json": json.dumps(raw_dict),
        })

        memo_combined = str(row["Memo"]) if pd.notna(row["Memo"]) else ""
        memo2 = str(row["Memo2"]) if pd.notna(row["Memo2"]) and str(row["Memo2"]).strip() else ""
        if memo2:
            memo_combined = memo_combined + memo2
        memo_combined = memo_combined.strip()

        amount_str = str(row["Amount"]).strip() if pd.notna(row["Amount"]) else "0"
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        date_str = str(row["Date"]).strip() if pd.notna(row["Date"]) else ""
        try:
            posted_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            posted_date = date_str

        source_account = str(row["Account"]).strip() if pd.notna(row["Account"]) else ""
        bank_txn_number = str(row["Number"]).strip() if pd.notna(row["Number"]) else ""
        bank_subcategory = str(row["Subcategory"]).strip() if pd.notna(row["Subcategory"]) else ""

        tx_id = _compute_tx_id(
            "barclays", source_account, posted_date, amount,
            None, None, memo_combined, bank_txn_number, row_number,
        )

        # Skip rows with no usable transaction data (e.g. footer/blank lines in Barclays CSV)
        if not posted_date and amount == 0 and not memo_combined.strip():
            continue

        match_text = _build_match_text(None, None, memo_combined, None)

        canonical_rows.append({
            "tx_id": tx_id,
            "raw_row_id": raw_row_id,
            "import_batch_id": import_batch_id,
            "source_bank": "barclays",
            "source_account": source_account,
            "posted_date": posted_date,
            "amount": amount,
            "currency": "GBP",
            "counterparty": None,
            "reference": None,
            "memo": memo_combined,
            "type": None,
            "balance": None,
            "bank_txn_number": bank_txn_number,
            "bank_category": None,
            "bank_subcategory": bank_subcategory,
            "effective_subcategory": bank_subcategory,
            "match_text": match_text,
            "description": None,
            "parent_tx_id": None,
            "is_superseded": 0,
        })

    return raw_rows, canonical_rows


def load_starling(filepath: str | Path, import_batch_id: str) -> tuple[list[dict], list[dict]]:
    """Load a Starling CSV and return (raw_rows, canonical_rows)."""
    filepath = Path(filepath)
    source_file = filepath.name

    for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
        try:
            df = pd.read_csv(filepath, dtype=str, encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        df = pd.read_csv(filepath, dtype=str, encoding="latin-1", errors="replace")

    df = df.fillna("")
    for c in df.columns:
        df[c] = df[c].astype(str)

    raw_rows = []
    canonical_rows = []

    for idx, row in df.iterrows():
        try:
            row_number = int(idx) + 1
        except (TypeError, ValueError):
            row_number = 1
        raw_row_id = f"{import_batch_id}_{source_file}_{row_number}"

        raw_dict = {k: str(row[k]) if pd.notna(row[k]) else "" for k in df.columns}
        raw_rows.append({
            "raw_row_id": raw_row_id,
            "import_batch_id": import_batch_id,
            "source_bank": "starling",
            "source_file": source_file,
            "row_number": row_number,
            "raw_json": json.dumps(raw_dict),
        })

        date_str = row.get("Date", "").strip()
        try:
            posted_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            posted_date = date_str

        counterparty = row.get("Counter Party", "").strip() or None
        reference = row.get("Reference", "").strip() or None
        notes = row.get("Notes", "").strip() or None
        txn_type = row.get("Type", "").strip() or None

        memo_parts = [p for p in [counterparty, reference, notes] if p]
        memo = " ".join(memo_parts) if memo_parts else None

        amount_str = row.get("Amount (GBP)", "0").strip()
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        balance_str = row.get("Balance (GBP)", "").strip()
        try:
            balance = float(balance_str)
        except ValueError:
            balance = None

        spending_category = row.get("Spending Category", "").strip() or None

        source_account = STARLING_ACCOUNT

        tx_id = _compute_tx_id(
            "starling", source_account, posted_date, amount,
            counterparty, reference, memo, None, row_number,
        )

        # Skip rows with no usable transaction data (e.g. trailing blank lines in Starling CSV)
        if not posted_date and amount == 0 and not (memo or counterparty or reference or notes):
            continue

        match_text = _build_match_text(counterparty, reference, memo, txn_type)

        canonical_rows.append({
            "tx_id": tx_id,
            "raw_row_id": raw_row_id,
            "import_batch_id": import_batch_id,
            "source_bank": "starling",
            "source_account": source_account,
            "posted_date": posted_date,
            "amount": amount,
            "currency": "GBP",
            "counterparty": counterparty,
            "reference": reference,
            "memo": memo,
            "type": txn_type,
            "balance": balance,
            "bank_txn_number": None,
            "bank_category": spending_category,
            "bank_subcategory": None,
            "effective_subcategory": spending_category,
            "match_text": match_text,
            "description": None,
            "parent_tx_id": None,
            "is_superseded": 0,
        })

    return raw_rows, canonical_rows


def load_month_files(bank_download_dir: Path, month_str: str, import_batch_id: str | None = None) -> tuple[list[dict], list[dict]]:
    """Load all four bank files for a month. month_str e.g. 'OCT2025'.
    Returns combined (raw_rows, canonical_rows).
    """
    if import_batch_id is None:
        import_batch_id = month_str

    dt = pd.to_datetime("01" + month_str, format="%d%b%Y")
    starling_date_str = dt.strftime("%Y-%m")

    barclays_files = [
        bank_download_dir / f"BC_6045_{month_str}.csv",
        bank_download_dir / f"BC_3072_{month_str}.csv",
        bank_download_dir / f"BC_4040_{month_str}.csv",
    ]
    starling_file = bank_download_dir / f"StarlingStatement_{starling_date_str}.csv"

    all_raw = []
    all_canonical = []

    for bf in barclays_files:
        if bf.exists():
            raw, canon = load_barclays(bf, import_batch_id)
            all_raw.extend(raw)
            all_canonical.extend(canon)
        else:
            print(f"Warning: missing Barclays file {bf}")

    if starling_file.exists():
        raw, canon = load_starling(starling_file, import_batch_id)
        all_raw.extend(raw)
        all_canonical.extend(canon)
    else:
        print(f"Warning: missing Starling file {starling_file}")

    all_canonical.sort(key=lambda r: r["posted_date"])
    return all_raw, all_canonical
