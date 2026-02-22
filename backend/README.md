# Property Review API

FastAPI backend for the property review frontend. Uses the same database and paths as the pipeline.

## Setup

From the **repo root**:

```bash
pip install -r backend/requirements.txt
```

If the database already existed before the review app was added, run once from repo root to create the `custom_list_entries` table: `python -m property_pipeline seed_db` (or `run_month MMMYYYY`).

Set environment variables (optional; defaults work for local dev):

- `REVIEW_APP_PASSWORD` – password for login (required in production)
- `JWT_SECRET` – secret for JWT signing (defaults to password)
- `DATA_PATH` – base path for `data/property` (default: repo `data/property`)
- `DB_PATH` – path to `labels.db`
- `CORS_ORIGINS` – comma-separated origins (default: `http://localhost:5173,http://localhost:3000`)

## Run

From the **repo root** (so `property_pipeline` can be imported):

```bash
set REVIEW_APP_PASSWORD=yourpassword
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Then open the frontend (see `frontend/README.md`) and log in with the same password.

## Deployment (VPS)

The `/api/months` (and other) endpoints read from the pipeline SQLite database. If the database file or its tables don't exist, you get **500 Internal Server Error**.

1. **Set paths** so the app can find/create the DB. On the VPS, either use the default (repo `data/property/labels.db`) or set env vars before starting the app:
   - `DATA_PATH` – directory that will contain `labels.db`, `bank-download/`, `generated/`, etc. (default: repo `data/property`).
   - Or set `DB_PATH` directly to the full path of `labels.db`.

2. **Create the data directory** if it doesn't exist, e.g.:
   ```bash
   mkdir -p data/property
   ```

3. **Create and seed the database** (from repo root, with the same `DATA_PATH`/`DB_PATH` if you set them):
   ```bash
   python -m property_pipeline seed_db
   ```
   This creates `labels.db` and all tables (rules, properties, transactions_canonical, etc.). Without this, the app will 500 on any endpoint that queries the DB.

4. **Optional:** To see months in the app, you need at least one month of data. After putting bank CSVs in `data/property/bank-download/`, run:
   ```bash
   python -m property_pipeline run_month OCT2025
   ```
   (Use the month that matches your bank files.) Until then, `/api/months` returns an empty list and the Home page will show "No months available" (which is valid, not an error).
