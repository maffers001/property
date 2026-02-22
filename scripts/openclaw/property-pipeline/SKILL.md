---
name: property-pipeline
description: Property rental analytics—bank CSVs from four accounts (Starling business, Barclays mortgages/personal/household) become categorised data for the monthly rent statement. Runs the pipeline (poll bank-download, import, review queue, finalize), prompt for review, and manage reports. Use when the user wants to process bank statements, import a month, do the monthly review workflow, finalize a month, run reports, or manage the property pipeline.
---

# Property Pipeline Skill

Use this skill when the user asks to **import bank data**, **process a month**, **check for new downloads**, **do the review**, **finalize**, or run **property reports**. All commands assume the repo root is the current working directory (e.g. `/home/openclaw/code/property` or project root).

## Background: what the pipeline is for

The pipeline supports **property rental analytics**: it turns raw bank exports into categorised transaction data used for the **monthly rent statement** and **financial summary**. Four bank accounts are combined each month:

- **Starling business (0055)** — rents in, property expenses out, director income.
- **Barclays joint (3072)** — mortgage payments for the flats.
- **Barclays personal (6045)** and **household (4040)** — personal/household spending.

**Flow:** Bank CSVs (one file per account per month) → pipeline imports and applies rules → each transaction gets **property code**, **category**, and **subcategory**. Low-confidence or rule-flagged rows go into a **review queue**. The user reviews and corrects labels (in Excel or the review app); the **finalized** file in `checked/` is then used by the **3.0 MonthlySummary** notebook to produce the statement and reports. The pipeline replaces the old notebook steps 1.0–2.0 and keeps the same deliverable: a checked spreadsheet ready for the monthly summary.

## 1. Poll for new bank downloads and run the pipeline

1. **Discover months with bank data**
   - Run: `python scripts/check_bank_downloads.py` to list all months that have any bank files (shows e.g. "2/4 files" or "complete").
   - The pipeline **waits for all four files** per month before running: BC_4040_MMMYYYY.csv, BC_3072_MMMYYYY.csv, BC_6045_MMMYYYY.csv, StarlingStatement_YYYY-MM.csv.

2. **Run the pipeline for new months**
   - Run: `python scripts/check_bank_downloads.py --run` to process **only** months that have all four files. Months with incomplete files are skipped until the full set is present.
   - Or run for a specific month (when you know all four are there): `python -m property_pipeline run_month MMMYYYY` (e.g. `OCT2025`). Add `--use-ml` if the user has trained an ML model.

3. **Prompt the user to do the review**
   - Tell the user: "Pipeline is done. Review queue files are in `data/property/review/review_queue_MMMYYYY.xlsx`. You can open them in Excel, or use the review app (start backend and frontend, then open the Queue page for that month). When you've finished reviewing, tell me and I'll finalize the month(s)."

## 2. After the user has completed review

- **Apply edits from the queue file** (if they edited the XLSX and want those applied):  
  `python -m property_pipeline review_month MMMYYYY`
- **Finalize** (copy draft to checked folder for the monthly statement):  
  `python -m property_pipeline finalize_month MMMYYYY`

## 3. Other actions the agent can do

| User intent | Action |
|-------------|--------|
| List months that have been processed / have data | `python scripts/check_bank_downloads.py` or list `data/property/generated/` for `*_codedAndCategorised.*` |
| Run pipeline for one month only | `python -m property_pipeline run_month MMMYYYY` |
| Wipe the database | `python scripts/wipe_db.py` (script will prompt for confirmation). |
| Seed the database (first-time or reset rules/properties) | `python -m property_pipeline seed_db` |
| Run reports (summary, outgoings, etc.) | Start the backend and tell the user to open the Reports page, or run the report_summary module if they want CLI/JSON. |
| Backtest rules vs checked XLSX | `python -m property_pipeline backtest` or `--months OCT2025 SEP2025` |
| Load historical labels from checked XLSX | `python -m property_pipeline load_historical` |
| Grade rules / train ML | `python -m property_pipeline grade_rules`, then `python -m property_pipeline train_ml` |

## 4. Paths (repo-relative)

- **Bank inputs:** `data/property/bank-download/` (BC_4040_MMMYYYY.csv, BC_3072_MMMYYYY.csv, BC_6045_MMMYYYY.csv, StarlingStatement_YYYY-MM.csv)
- **Pipeline outputs:** `data/property/generated/`, `data/property/review/` (review_queue_MMMYYYY.xlsx)
- **Final checked (for 3.0 statement):** `data/property/checked/`
- **Database:** `data/property/labels.db` (or `DB_PATH` env)

## 5. Review app (optional)

If the user prefers the web app for review: from repo root, set `REVIEW_APP_PASSWORD` and run `uvicorn backend.main:app --reload --port 8000`, then `cd frontend && npm run dev`. They can use Draft and Queue pages to correct labels; the app persists to the DB and updates the review queue XLSX so they can stop and resume later.
