# Property Pipeline

Single callable Python program that combines notebooks 1.0, 1.5 and 2.0: load bank CSVs → canonical format → property codes → categories/subcategories → output compatible with 3.0 MonthlySummary.

## Setup

```bash
pip install -r requirements.txt
```

## Commands

- **Seed database** (creates `data/property/labels.db`, rules, properties):
  ```bash
  python -m property_pipeline seed_db
  ```

- **Process a month** (reads from `data/property/bank-download/`, writes to `data/property/generated/` and `data/property/review/`):
  ```bash
  python -m property_pipeline run_month OCT2025
  ```

- **Finalize** (copy draft to checked folder for 3.0):
  ```bash
  python -m property_pipeline finalize_month OCT2025
  ```

- **Apply review corrections** (from edited review queue XLSX):
  ```bash
  python -m property_pipeline review_month OCT2025
  ```

- **Backtest** against XLSX ground truth in `data/property/checked/`:
  ```bash
  python -m property_pipeline backtest
  python -m property_pipeline backtest --months OCT2025 SEP2025
  ```

## Why backtest doesn't use the database

**Backtest** uses a separate, self-contained path so you can measure accuracy without touching the DB or running the full pipeline:

1. It reads the same **bank CSVs** from `bank-download/`.
2. It loads **rules and properties** from code (`rules_seed.py`), not from the DB.
3. It runs the **rule engine in memory** on the loaded transactions and gets labels.
4. It loads **ground truth** from the XLSX (or CSV) in `checked/` and compares row-by-row.

So backtest never opens `labels.db`. It only needs bank files + checked XLSX. The **full pipeline** (`run_month`) does use the DB: it stores raw rows, canonical transactions, and labels there so you can review, correct, and finalize later. Backtest is for measuring how well the rules behave; the DB is for the live workflow.

## Backups

Before overwriting any output file, the pipeline creates a timestamped backup (e.g. `OCT2025_codedAndCategorised.xlsx.bak_20250218-143022`). This applies to files written in `generated/`, `review/`, and when running `finalize_month` to `checked/`.

## Docker

```bash
docker compose build
docker compose run --rm pipeline run_month OCT2025
```

Volumes: `./data/property` is mounted so `labels.db` and outputs persist.

## Outputs

- `generated/MMMYYYY_codedAndCategorised.xlsx` (and .csv) – draft for manual check
- `review/review_queue_MMMYYYY.xlsx` – rows with needs_review=1
- `generated/DDCheck_MMMYYYY.csv` – direct debits + Beals
- `generated/CatCheck_MMMYYYY.csv` – all categorised rows

After manual check, run `finalize_month MMMYYYY` to copy to `checked/` for the monthly statement notebook.
