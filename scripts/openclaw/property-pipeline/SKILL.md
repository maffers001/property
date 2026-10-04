---
name: property-pipeline
description: Property rental analytics—bank CSVs from four accounts (Starling business, Barclays mortgages/personal/household) become categorised data for the monthly rent statement. Runs the pipeline (poll bank-download, import, Review App, finalize), prompt for review, and manage reports. Use when the user wants to process bank statements, import a month, do the monthly review workflow, finalize a month, run reports, or manage the property pipeline.
---

# Property Pipeline Skill

Use this skill when the user asks to **import bank data**, **process a month**, **check for new downloads**, **do the review**, **finalize**, or run **property reports**. All commands assume the repo root is the current working directory (e.g. `/home/openclaw/code/property` or project root).

**Requirements:** The pipeline and Review App require **Python 3.13.11**.

## Background: what the pipeline is for

The pipeline supports **property rental analytics**: it turns raw bank exports into categorised transaction data used for the **monthly rent statement** and **financial summary**. Four bank accounts are combined each month:

- **Starling business (0055)** — rents in, property expenses out, director income.
- **Barclays joint (3072)** — mortgage payments for the flats.
- **Barclays personal (6045)** and **household (4040)** — personal/household spending.

**Flow:** Bank CSVs (one file per account per month) → pipeline imports and applies rules → each transaction gets **property code**, **category**, and **subcategory**. Low-confidence or rule-flagged rows are marked `needs_review=1`. The user reviews and corrects labels in the **Review App**; the **finalized** file in `checked/` is then used by the **3.0 MonthlySummary** notebook. The pipeline replaces the old notebook steps 1.0–2.0 and keeps the same deliverable: a checked spreadsheet ready for the monthly summary.

## 1. Poll for new bank downloads and run the pipeline

1. **Discover months with bank data**
   - Put raw downloads in `data/property/bank-download/incoming/` then run `python scripts/preprocess_bank_downloads.py`. That splits Barclays (one file per account, any date range, newest-first) into monthly `BC_*_MMMYYYY.csv` (oldest to newest, UTF-8) and rewrites Starling monthly files as UTF-8 `StarlingStatement_YYYY-MM.csv` into `data/property/bank-download/`.
   - Run: `python scripts/check_bank_downloads.py` to list all months that have any bank files (shows e.g. "2/4 files" or "complete").
   - The pipeline **waits for all four files** per month before running: BC_4040_MMMYYYY.csv, BC_3072_MMMYYYY.csv, BC_6045_MMMYYYY.csv, StarlingStatement_YYYY-MM.csv.

2. **Run the pipeline for new months**
   - Run: `python scripts/check_bank_downloads.py --run` to process **only** months that have all four files. Months with incomplete files are skipped until the full set is present. Months already in `labels.db` are skipped (pass `--yes` only if you intend to wipe and re-import).
   - Or run for a specific month (when you know all four are there): `python -m property_pipeline run_month MMMYYYY` (e.g. `OCT2025`). If that month is already imported, type the month code to confirm (or `--yes`). A snapshot is written to `data/property/backups/` first. Add `--use-ml` if the user has trained an ML model.

3. **Prompt the user to do the review**
   - Tell the user: "Pipeline is done. Open the Review App (http://localhost:5173), pick the month, and work through rows that need review (the page defaults to that filter). When you've finished, tell me and I'll finalize the month(s)."

## 2. After the user has completed review

- **Finalize** (write `checked/` from the database for the monthly statement):  
  `python -m property_pipeline finalize_month MMMYYYY`

## 3. Other actions the agent can do

| User intent | Action |
|-------------|--------|
| List months that have been processed / have data | `python scripts/check_bank_downloads.py` or list `data/property/generated/` for `*_codedAndCategorised.*` |
| Run pipeline for one month only | `python -m property_pipeline run_month MMMYYYY` |
| Wipe the database | `python scripts/wipe_db.py` (script will prompt for confirmation). |
| Seed the database (first-time or reset rules/properties) | From repo root: `python -m property_pipeline seed_db`. See §4 for details. |
| Run reports (summary, outgoings, etc.) | Start the backend and tell the user to open the Reports page, or run the report_summary module if they want CLI/JSON. |
| Backtest rules vs checked XLSX | `python -m property_pipeline backtest` or `--months OCT2025 SEP2025` |
| Load historical labels from checked XLSX | `python -m property_pipeline load_historical` |
| Grade rules / train ML | `python -m property_pipeline grade_rules`, then `python -m property_pipeline train_ml` |

## 4. Seeding the database

The pipeline and Review App use a SQLite database at `data/property/labels.db`. It must exist and have all tables before running `run_month` or the Review App (otherwise the app returns 500 on endpoints like `/api/months`).

**How to seed the database** (from repo root):

```bash
python -m property_pipeline seed_db
```

- **When to run:** Before the first `run_month` or before starting the Review App; also after wiping the DB with `scripts/wipe_db.py` if you want to use the app again.
- **What it does:** Creates `data/property/labels.db` if missing, creates all tables (e.g. `transactions_canonical`, `transactions_labels`, `rules`, `properties`, `custom_list_entries`), and seeds rules and property codes from the pipeline’s seed data.
- **Custom paths:** If you use a different data location, set `DATA_PATH` or `DB_PATH` when running the app and when running `seed_db`, e.g. `DATA_PATH=/var/lib/property python -m property_pipeline seed_db`.

After seeding, `/api/months` will return an empty list until you run `run_month MMMYYYY` for at least one month (with bank files in `data/property/bank-download/`).

## 5. Paths (repo-relative)

- **Bank inputs:** `data/property/bank-download/` (BC_4040_MMMYYYY.csv, BC_3072_MMMYYYY.csv, BC_6045_MMMYYYY.csv, StarlingStatement_YYYY-MM.csv)
- **Pipeline outputs:** `data/property/generated/`
- **Final checked (for 3.0 statement):** `data/property/checked/`
- **Database:** `data/property/labels.db` (or `DB_PATH` env)
- **DB snapshots:** `data/property/backups/` (taken before `run_month` re-import and before `wipe_db`)

## 6. Review app

The **Review App** is a web UI (React frontend + FastAPI backend) for reviewing and correcting transaction labels. It reads and writes the same database as the pipeline. Changes are saved immediately to the DB. You can stop and resume later.

**What it does:**
- **Home** — Pick a month; see how many transactions need review; open Review or Reports.
- **Review** (`/review/:month`) — All transactions for the month, defaulting to **Needs review only**. Filter by property, category, subcategory, search, date. Edit **Property**, **Category**, and **Subcategory** inline. Add or remove the needs-review flag; **Mark reviewed** or **Done reviewing**. Optional **Save as rule**. Download CSV of the current view. Shows sum of amount for visible rows.
- **Reports** — Month or date-range summary: property summary, outgoings, personal spending.
- **Rules** — Edit categorisation regexes.
- **Settings** — Add new property codes, categories, or subcategories.

**How to run the Review App:**

1. **Backend** (from repo root). Set the login password and start the API:
   ```bash
   set REVIEW_APP_PASSWORD=yourpassword
   uvicorn backend.main:app --reload --port 8000
   ```
   (On Unix/macOS use `export REVIEW_APP_PASSWORD=yourpassword`.) Leave this terminal running.

2. **Frontend** (new terminal, from repo root):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The dev server usually runs at http://localhost:5173 and proxies `/api` to the backend.

3. **Use the app:** Open http://localhost:5173 in a browser. Log in with the same value as `REVIEW_APP_PASSWORD`. Choose a month on Home, then open **Review {month}**. When finished, tell the agent to finalize the month(s).
