# Monthly process

Do this from the **repo root**. Python **3.13.11**. Password for the Review App is `REVIEW_APP_PASSWORD` (local default: `yourpassword`).

1. **Bank files** — Drop raw downloads in `data/property/bank-download/incoming/`, then:

   `python scripts/preprocess_bank_downloads.py`

   You need four files per month in `data/property/bank-download/`:  
   `BC_4040_MMMYYYY.csv`, `BC_3072_MMMYYYY.csv`, `BC_6045_MMMYYYY.csv`, `StarlingStatement_YYYY-MM.csv`.

2. **Import** — New months only:

   `python scripts/check_bank_downloads.py --run`

   Or one month: `python -m property_pipeline run_month MMMYYYY`  
   Do **not** re-run a month you have already reviewed (it wipes that month’s labels). You will be asked to type the month code; a DB snapshot is taken if you proceed. See `BACKUP.md`.

3. **Review** — Start the app (Windows: **no** `--reload`):

   ```
   set REVIEW_APP_PASSWORD=yourpassword
   uvicorn backend.main:app --port 8000
   ```

   Other terminal: `cd frontend && npm run dev` → http://localhost:5173  
   Open **Review {month}**. Property/Cat/Subcat save as you change them. Save as rule if the pattern should apply later. Mark reviewed when done with a row. Undo appears for ~12 seconds.

4. **Finalize** — Writes `data/property/checked/MMMYYYY_codedAndCategorised.xlsx` from the DB:

   `python -m property_pipeline finalize_month MMMYYYY`

5. **Statement** — Use that checked `.xlsx` in notebook **3.0 MonthlySummary**.

New tenancy: add a row in `data/property/bank-download/all_tenancies.xls` and set the previous tenant’s end date.

First-time or empty DB: `python -m property_pipeline seed_db`.
