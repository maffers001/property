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
