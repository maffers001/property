#!/usr/bin/env python3
"""Split/normalise raw bank downloads into monthly CSVs the pipeline expects.

Drop files into data/property/bank-download/incoming/ then run from repo root:

    python scripts/preprocess_bank_downloads.py

Barclays: one file per account (4040 / 3072 / 6045), any date range, newest-first OK.
  → BC_{account}_MMMYYYY.csv (oldest to newest, UTF-8)

Starling: one file per month (any encoding).
  → StarlingStatement_YYYY-MM.csv (UTF-8)

Outputs go to data/property/bank-download/ (not incoming/).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from property_pipeline.config import BANK_DOWNLOAD_DIR
from property_pipeline.importers import read_csv_encoded

INCOMING_DIR = BANK_DOWNLOAD_DIR / "incoming"
MONTH_ABBR = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
BARCLAYS_ACCOUNTS = ("4040", "3072", "6045")
BARCLAYS_COLS = ["Number", "Date", "Account", "Amount", "Subcategory", "Memo"]
SKIP_NAMES = {"desktop.ini"}


def _account_from_name_or_rows(path: Path, df: pd.DataFrame) -> str | None:
    name = path.name.upper()
    for acct in BARCLAYS_ACCOUNTS:
        if acct in name:
            return acct
    if "Account" in df.columns:
        sample = " ".join(df["Account"].astype(str).head(20).tolist())
        for acct in BARCLAYS_ACCOUNTS:
            if acct in sample:
                return acct
    return None


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.astype(str).str.strip(), dayfirst=True, errors="coerce")


def _sort_oldest_first(df: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    out = df.copy()
    out["_dt"] = dates
    valid = out.dropna(subset=["_dt"])
    if valid.empty:
        return df
    first, last = valid["_dt"].iloc[0], valid["_dt"].iloc[-1]
    if first > last:
        out = out.iloc[::-1].reset_index(drop=True)
    out = out.sort_values("_dt", kind="mergesort")
    return out.drop(columns=["_dt"])


def _load_barclays_df(path: Path) -> pd.DataFrame:
    df = read_csv_encoded(path, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    # Drop unnamed extra columns from trailing commas
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]
    for c in BARCLAYS_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[BARCLAYS_COLS].copy()
    df = df.fillna("")
    for c in BARCLAYS_COLS:
        df[c] = df[c].astype(str).str.replace("\t", "", regex=False).str.strip()
    return df


def _is_starling(path: Path, df: pd.DataFrame) -> bool:
    cols = {c.strip().lower() for c in df.columns}
    if "counter party" in cols or "counterparty" in cols:
        return True
    return path.name.lower().startswith("starling")


def process_barclays(path: Path, out_dir: Path) -> list[str]:
    df = _load_barclays_df(path)
    acct = _account_from_name_or_rows(path, df)
    if not acct:
        print(f"  skip (not a Barclays account file): {path.name}")
        return []
    dates = _parse_dates(df["Date"])
    df = _sort_oldest_first(df, dates)
    dates = _parse_dates(df["Date"])
    written = []
    for (year, month), group in df.groupby([dates.dt.year, dates.dt.month], sort=True):
        if pd.isna(year) or pd.isna(month):
            continue
        month_str = f"{MONTH_ABBR[int(month) - 1]}{int(year)}"
        dest = out_dir / f"BC_{acct}_{month_str}.csv"
        group[BARCLAYS_COLS].to_csv(dest, index=False, encoding="utf-8")
        written.append(f"{dest.name} ({len(group)} rows)")
    return written


def process_starling(path: Path, out_dir: Path) -> list[str]:
    df = read_csv_encoded(path, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.fillna("")
    date_col = next((c for c in df.columns if c.lower() == "date"), None)
    dest_name = path.name
    m = re.match(r"^StarlingStatement_(\d{4})-(\d{2})\.csv$", path.name, re.I)
    if m:
        dest_name = f"StarlingStatement_{m.group(1)}-{m.group(2)}.csv"
    elif date_col:
        dates = _parse_dates(df[date_col])
        valid = dates.dropna()
        if not valid.empty:
            dest_name = f"StarlingStatement_{valid.iloc[0].strftime('%Y-%m')}.csv"
            df = _sort_oldest_first(df, dates)
    dest = out_dir / dest_name
    df.to_csv(dest, index=False, encoding="utf-8")
    return [f"{dest.name} (UTF-8, {len(df)} rows)"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Split/normalise raw bank CSVs into monthly files")
    parser.add_argument(
        "incoming",
        nargs="?",
        default=str(INCOMING_DIR),
        help="Folder with raw downloads (default: data/property/bank-download/incoming)",
    )
    parser.add_argument(
        "--out",
        default=str(BANK_DOWNLOAD_DIR),
        help="Output folder (default: data/property/bank-download)",
    )
    args = parser.parse_args()

    incoming = Path(args.incoming)
    out_dir = Path(args.out)
    incoming.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = [p for p in incoming.iterdir() if p.is_file() and p.suffix.lower() == ".csv" and p.name not in SKIP_NAMES]
    if not files:
        print(f"No CSVs in {incoming}")
        print("Put the 3 Barclays files and the Starling monthly files there, then re-run.")
        return

    print(f"Incoming: {incoming}")
    print(f"Output:   {out_dir}")
    for path in sorted(files):
        peek = read_csv_encoded(path, dtype=str, nrows=5)
        peek.columns = [str(c).strip() for c in peek.columns]
        print(f"\n{path.name}")
        if _is_starling(path, peek):
            for line in process_starling(path, out_dir):
                print(f"  -> {line}")
        else:
            for line in process_barclays(path, out_dir):
                print(f"  -> {line}")


if __name__ == "__main__":
    main()
