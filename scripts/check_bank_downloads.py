#!/usr/bin/env python3
"""Poll bank-download directory for bank CSVs and list months that have data.
Useful for OpenClaw or automation to decide when to run the pipeline.

Bank files per month:
  BC_4040_MMMYYYY.csv, BC_3072_MMMYYYY.csv, BC_6045_MMMYYYY.csv,
  StarlingStatement_YYYY-MM.csv
"""

import re
import sys
from pathlib import Path

# Run from repo root
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from property_pipeline.config import BANK_DOWNLOAD_DIR

BARCLAYS_PATTERN = re.compile(r"^BC_(?:4040|3072|6045)_([A-Z]{3}\d{4})\.csv$", re.IGNORECASE)
STARLING_PATTERN = re.compile(r"^StarlingStatement_(\d{4})-(\d{2})\.csv$", re.IGNORECASE)

# Map (year, month) to MMMYYYY
MONTH_ABBR = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def _starling_to_month_str(year: int, month: int) -> str:
    return f"{MONTH_ABBR[month - 1]}{year}"


def discover_months(bank_download_dir: Path) -> dict[str, list[str]]:
    """Return dict: month_str -> list of filenames present for that month."""
    months: dict[str, list[str]] = {}
    if not bank_download_dir.exists():
        return months

    for p in bank_download_dir.iterdir():
        if not p.is_file():
            continue
        name = p.name
        m_barclays = BARCLAYS_PATTERN.match(name)
        if m_barclays:
            month_str = m_barclays.group(1).upper()
            months.setdefault(month_str, []).append(name)
            continue
        m_starling = STARLING_PATTERN.match(name)
        if m_starling:
            year, month = int(m_starling.group(1)), int(m_starling.group(2))
            month_str = _starling_to_month_str(year, month)
            months.setdefault(month_str, []).append(name)
            continue

    return months


def expected_files(month_str: str) -> list[str]:
    """Return the four expected filenames for this month (MMMYYYY)."""
    import pandas as pd
    dt = pd.to_datetime("01" + month_str, format="%d%b%Y")
    starling_date = dt.strftime("%Y-%m")
    return [
        f"BC_6045_{month_str}.csv",
        f"BC_3072_{month_str}.csv",
        f"BC_4040_{month_str}.csv",
        f"StarlingStatement_{starling_date}.csv",
    ]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="List months with bank data in bank-download/")
    parser.add_argument(
        "dir",
        nargs="?",
        default=None,
        help="Bank download directory (default: data/property/bank-download)",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Only list months that have all four expected files",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run pipeline (run_month) for each discovered month",
    )
    parser.add_argument(
        "--use-ml",
        action="store_true",
        help="Pass --use-ml to run_month when using --run",
    )
    args = parser.parse_args()

    bank_dir = Path(args.dir) if args.dir else BANK_DOWNLOAD_DIR
    months_map = discover_months(bank_dir)

    if not months_map:
        print("No bank files found.")
        if args.dir:
            print(f"  Directory: {bank_dir}")
        else:
            print(f"  Directory: {bank_dir} (set DATA_PATH or pass dir)")
        return

    # Sort by month (roughly chronological)
    try:
        import pandas as pd
        sorted_months = sorted(
            months_map.keys(),
            key=lambda m: pd.to_datetime("01" + m, format="%d%b%Y"),
        )
    except Exception:
        sorted_months = sorted(months_map.keys())

    # When --run is used, only process months that have all four files
    require_complete = args.require_all or args.run
    if require_complete:
        complete = []
        for month in sorted_months:
            have = set(months_map[month])
            need = set(expected_files(month))
            if need.issubset(have):
                complete.append(month)
        sorted_months = complete

    for month in sorted_months:
        files = months_map[month]
        status = "complete" if len(files) >= 4 else f"{len(files)}/4 files"
        print(f"  {month}: {status}")

    if args.run and sorted_months:
        from property_pipeline.pipeline import run_month
        for month in sorted_months:
            print(f"\nRunning pipeline for {month}...")
            run_month(month, use_ml=args.use_ml)
        print("\nDone. Review queue files: data/property/review/review_queue_MMMYYYY.xlsx")
        print("Or open the review app, then run finalize_month when review is complete.")
    elif args.run and not sorted_months:
        print("\nNo month has all four bank files yet. Add the missing files and run again.")


if __name__ == "__main__":
    main()
