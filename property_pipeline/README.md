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
  python -m property_pipeline run_month OCT2025 --use-ml   # use ML for catch-all / low-confidence rows
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

- **`generated/MMMYYYY_codedAndCategorised.xlsx`** (and .csv) – main draft: all transactions with property/category/subcategory and confidence. Use this for manual check and as the source for finalizing.
- **`review/review_queue_MMMYYYY.xlsx`** – subset of rows that need human review (`needs_review=1`, e.g. low confidence or force-review threshold). Same columns as the draft but only the flagged rows.
- **`generated/DDCheck_MMMYYYY.csv`** – diagnostic: direct debits and Beals only (rows where `effective_subcategory` contains “Direct Debit” or `memo` matches `BEALS...`). For checking mortgage/DD lines.
- **`generated/CatCheck_MMMYYYY.csv`** – diagnostic: all categorised transactions (canonical + labels merged, sorted by date). Full list for category/audit checks.

After manual check, run `finalize_month MMMYYYY` to copy the draft to `checked/` for the monthly statement notebook.

## Review process

The review queue is the list of transactions the pipeline is unsure about. You correct them in the queue file, then write those corrections back into the database.

**Step 1 – Run the pipeline**  
```bash
python -m property_pipeline run_month OCT2025
```
This creates the main draft and **`review/review_queue_OCT2025.xlsx`**: only transactions with `needs_review=1` (e.g. low confidence, catch-all rule, or below auto-accept threshold).

**Step 2 – Open and edit the review queue**  
- Open `data/property/review/review_queue_MMMYYYY.xlsx`.  
- For each row, fix **property_code**, **category**, and **subcategory** if they’re wrong.  
- You can **delete rows** you don’t want to change (e.g. junk or duplicates); `review_month` only applies rows that are still in the file.  
- Save the file.

**Step 3 – Apply corrections to the database**  
```bash
python -m property_pipeline review_month OCT2025
```
The script reads the saved review queue and, for each row in it, inserts a new label version in `transactions_labels` with `source='manual'`, `confidence=1.0`, and `reviewed=1`. Those corrections are then used by `grade_rules` and `train_ml`.

**Step 4 – Finalize**  
When the draft (and any review edits) are correct, copy it to `checked/` for the monthly statement:
```bash
python -m property_pipeline finalize_month OCT2025
```
You can run `finalize_month` more than once: each time it backs up the existing file in `checked/` (timestamped) then copies the current draft from `generated/` over. The **draft in `generated/` is not updated when you run `review_month`** — the draft is only written by `run_month`. Corrections you apply via the review queue are stored in the database (for `grade_rules` and `train_ml`), but the draft file still has the labels from the last `run_month`. To have your manual corrections in the finalized file, edit the draft XLSX/CSV in `generated/` to match your fixes, then run `finalize_month`.

**Correcting transactions that weren’t in the review queue**  
If you spot an error on a transaction that was *not* flagged for review (e.g. the pipeline was confident but wrong), add it to the review queue: open `review/review_queue_MMMYYYY.xlsx`, add a row with the same columns (at least **tx_id**, **property_code**, **category**, **subcategory** — you can copy a row from the main draft and fix the three label fields). Save, then run `review_month MMMYYYY`. The script applies every row in the file; it doesn’t matter whether the row was originally in the queue.

**Running review_month more than once**  
You can run `review_month` again after making further corrections: edit the review queue, save, and run the command again. Each run inserts a **new** label version for every row in the file (it does not check if the values changed). So running it multiple times when you have new edits is fine and intended. Note that `review_month` is **not idempotent**: if you run it again with the same file and no edits, you will get duplicate label versions (same content, higher version numbers). The “current” label (latest version) is still correct, but avoid re-running with an unchanged file.

