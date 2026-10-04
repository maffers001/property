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

- **Process a month** (reads from `data/property/bank-download/`, writes to `data/property/generated/`):
  ```bash
  python -m property_pipeline run_month OCT2025
  python -m property_pipeline run_month OCT2025 --use-ml   # use ML for catch-all / low-confidence rows
  ```
  Re-running for the same month **cleans that month’s data first** (canonical, labels, raw rows), then re-imports from the bank files, so you get a full replace. If the month is already in the DB you must confirm by typing the month code (or pass `--yes`). A SQLite snapshot is written first. Trailing blank lines in Barclays and Starling CSVs are skipped and not stored as transactions.

- **Finalize** (copy draft to checked folder for 3.0):
  ```bash
  python -m property_pipeline finalize_month OCT2025
  ```

- **Backtest** against XLSX ground truth in `data/property/checked/`:
  ```bash
  python -m property_pipeline backtest
  python -m property_pipeline backtest --months OCT2025 SEP2025
  ```

- **Load historical ground truth** (bulk import checked XLSX into DB as manual labels):
  ```bash
  python -m property_pipeline load_historical
  python -m property_pipeline load_historical --months OCT2025 SEP2025
  ```

- **Grade rules** (compute rule_performance from historical labels; run after load_historical):
  ```bash
  python -m property_pipeline grade_rules
  ```

- **Train ML model** (trains on historical labels in DB; saves to `data/property/ml_model.joblib`):
  ```bash
  python -m property_pipeline train_ml
  python -m property_pipeline train_ml --db path/to/labels.db --model path/to/model.joblib
  ```
  Requires at least 20 labeled transactions. Run after `load_historical` (and optionally `grade_rules`).

## Phase 3: Confidence and optional ML

- **Confidence from rule_performance**  
  When you run `grade_rules`, the pipeline fills the `rule_performance` table with per-rule accuracy (category, subcategory, property). `run_month` loads this and uses it to set **base confidence**: if the winning rule has measured accuracy, confidence is derived from that (blended with strength-based fallback). Rules without performance data still use strength-only confidence.

- **Optional ML model**  
  An ML model can suggest labels for transactions where the rule engine is weak (e.g. catch-all or low confidence). Regex rules keep **precedence**: ML only overrides when the rule label is from a catch-all rule or confidence is below 0.85, and only when the ML prediction confidence is above 0.9. Corrections you make (e.g. via review) stay in `transactions_labels` and can be used the next time you run `train_ml`.

  - **Train the model** (after loading historical labels):
    ```bash
    python -m property_pipeline train_ml
    ```
  - **Use ML in run_month**:
    ```bash
    python -m property_pipeline run_month OCT2025 --use-ml
    python -m property_pipeline run_month OCT2025 --use-ml --model path/to/ml_model.joblib
    ```
  Model path defaults to `data/property/ml_model.joblib` (overridable with `MODEL_PATH` or `--model`).

## Why backtest doesn't use the database

**Backtest** uses a separate, self-contained path so you can measure accuracy without touching the DB or running the full pipeline:

1. It reads the same **bank CSVs** from `bank-download/`.
2. It loads **rules and properties** from code (`rules_seed.py`), not from the DB.
3. It runs the **rule engine in memory** on the loaded transactions and gets labels.
4. It loads **ground truth** from the XLSX (or CSV) in `checked/` and compares row-by-row.

So backtest never opens `labels.db`. It only needs bank files + checked XLSX. The **full pipeline** (`run_month`) does use the DB: it stores raw rows, canonical transactions, and labels there so you can review, correct, and finalize later. Backtest is for measuring how well the rules behave; the DB is for the live workflow.

## Backups

Before overwriting any output file, the pipeline creates a timestamped backup (e.g. `OCT2025_codedAndCategorised.xlsx.bak_20250218-143022`). This applies to files written in `generated/`, `review/`, and when running `finalize_month` to `checked/`.

Before `run_month` clears a month (and before `scripts/wipe_db.py` empties the DB), a consistent copy of `labels.db` is written to `data/property/backups/` via SQLite backup, plus `learned_rules.json` if it exists. The last 10 snapshots are kept (`BACKUP_KEEP`). Restore by stopping the Review App, copying a snapshot over `labels.db`, and copying the matching `.learned_rules.json` over `learned_rules.json` if needed. Step-by-step: **`documentation/BACKUP.md`**. Monthly steps: **`documentation/PROCESS.md`**.

## Where is the database?

The database is a single SQLite file: **`data/property/labels.db`** on your machine (or in the repo). It is created the first time you run `seed_db` or `run_month` — there is no separate database server or container.

- **Running locally:** `python -m property_pipeline run_month OCT2025` creates or uses `data/property/labels.db` on the host.
- **Running in Docker:** `docker compose run --rm pipeline run_month OCT2025` uses the same path inside the container. Because `./data/property` is mounted into the container, the file is written to `data/property/labels.db` on the host, so you see it in your project folder. The DB is not “inside” the container; it lives in the mounted directory.

So you won’t see a “database” container in Docker — only the pipeline container that reads/writes the SQLite file in the shared volume.

**Why no dedicated DB container?** SQLite is an embedded, file-based database: the database *is* the file. There is no separate server process (unlike PostgreSQL or MySQL). The pipeline opens `labels.db` directly when it runs. So there’s nothing to run in a second container — with SQLite, the “database” is just this file.

## Connect and query the database

**Command line (sqlite3)**  
If `sqlite3` is installed, open the DB and run SQL:

```bash
sqlite3 data/property/labels.db
```

Then e.g. `.tables`, `SELECT * FROM rules LIMIT 5;`, `SELECT * FROM transactions_canonical WHERE import_batch_id = 'OCT2025' LIMIT 10;`. Use `.quit` to exit.

**Python (same as the pipeline)**  
Use the pipeline’s DB helpers so path and WAL are consistent:

```python
from property_pipeline.db import get_db

with get_db() as conn:
    for row in conn.execute("SELECT tx_id, posted_date, amount, memo FROM transactions_canonical WHERE import_batch_id = 'OCT2025' LIMIT 5"):
        print(dict(row))
```

Or with a custom path: `get_db("path/to/labels.db")`. Rows are `sqlite3.Row` (e.g. `row["tx_id"]`).

**GUI**  
Point any SQLite client at `data/property/labels.db`, e.g. [DB Browser for SQLite](https://sqlitebrowser.org/), DBeaver, or the SQLite extension in VS Code.

## Docker

```bash
docker compose build
docker compose run --rm pipeline run_month OCT2025
```

Volumes: `./data/property` is mounted so `labels.db` and all outputs are created on the host under `data/property/` and persist after the container exits.

## Outputs

After `run_month MMMYYYY` you get:

- **`generated/MMMYYYY_codedAndCategorised.xlsx`** (and .csv) – full month with property/category/subcategory and confidence. Snapshot only; review in the Review App.
- **`generated/DDCheck_MMMYYYY.csv`** – diagnostic: direct debits and Beals.
- **`generated/CatCheck_MMMYYYY.csv`** – diagnostic: all categorised transactions.

**Dropdown validation in XLSX**
The generated XLSX includes a **Lists** sheet and Excel dropdowns on Property, Cat, and Subcat. Add new values on the Lists sheet if you open the file in Excel.

## Review process

Review happens in the **Review App**, which writes labels to `labels.db`. There is no review-queue spreadsheet in the normal flow.

1. `python -m property_pipeline run_month OCT2025`
2. Open the Review App and choose **Review OCT2025**. It defaults to rows with `needs_review=1`. Uncheck **Needs review only** to see the whole month. Edit Property/Cat/Subcat, optionally **Save as rule**, then **Mark reviewed** or **Done reviewing**.
3. `python -m property_pipeline finalize_month OCT2025` writes `checked/` (and updates `generated/`) from the database.

OurRent, PropertyExpense, and Mortgage without a property code are always flagged for review.

`review_month` remains as a legacy command if an old `review/review_queue_*.xlsx` still exists; it is not part of the current workflow.
