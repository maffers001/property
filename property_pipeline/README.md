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

- **Load historical ground truth** (bulk import checked XLSX into DB as manual labels):
  ```bash
  python -m property_pipeline load_historical
  python -m property_pipeline load_historical --months OCT2025 SEP2025
  ```

- **Grade rules** (compute rule_performance from historical labels; run after load_historical):
  ```bash
  python -m property_pipeline grade_rules
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

- `generated/MMMYYYY_codedAndCategorised.xlsx` (and .csv) – draft for manual check
- `review/review_queue_MMMYYYY.xlsx` – rows with needs_review=1
- `generated/DDCheck_MMMYYYY.csv` – direct debits + Beals
- `generated/CatCheck_MMMYYYY.csv` – all categorised rows

After manual check, run `finalize_month MMMYYYY` to copy to `checked/` for the monthly statement notebook.
