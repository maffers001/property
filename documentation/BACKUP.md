# Backing up review data

Review work lives in **files on disk**, not in a separate database server. Git does not reliably keep `labels.db` (it is local/untracked). Copy the files below if you care about in-progress months.

For the monthly steps see `PROCESS.md`. For CLI extras see `property_pipeline/README.md`.

## What to keep

| File / folder | Why |
|---------------|-----|
| `data/property/labels.db` | Transactions and Property/Cat/Subcat labels from the Review App |
| `data/property/learned_rules.json` | Rules saved in the app (survives `seed_db`; not wiped by `run_month`) |
| `data/property/checked/` | Final month workbooks for notebook 3.0 |
| `data/property/bank-download/` | Source bank CSVs |
| `data/property/backups/` | Automatic DB snapshots (see below) |

Optional: `generated/` is a draft export. After `finalize_month` it matches the DB; during review it can be stale.

If `labels.db` is open (Review App / uvicorn running), you may also see `labels.db-wal` and `labels.db-shm`. A **manual** copy of `labels.db` alone can be incomplete. Prefer the automatic snapshots, or stop the app first then copy `labels.db` plus any `-wal`/`-shm` files.

## Automatic snapshots

The pipeline writes a consistent SQLite copy (WAL-safe) to `data/property/backups/` whenever `labels.db` already exists and you run:

- `python -m property_pipeline run_month MMMYYYY` (every import, including a *new* month while other months are in the DB; if **this** month is already imported you must type the month code or pass `--yes` first)
- `python scripts/wipe_db.py` after you type `y`

Each snapshot is a pair, for example:

```
data/property/backups/labels_before-run_JAN2026_20261004-195800.db
data/property/backups/labels_before-run_JAN2026_20261004-195800.learned_rules.json
```

The last **10** snapshots are kept (`BACKUP_KEEP` env var). Older files are deleted.

`check_bank_downloads.py --run` does **not** re-import months already in the DB unless you pass `--yes`.

## Manual copy (anytime)

Stop the Review App (uvicorn) first, then from the repo root:

**Windows (PowerShell)**

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path data\property\backups | Out-Null
Copy-Item data\property\labels.db "data\property\backups\labels_manual_$stamp.db"
if (Test-Path data\property\learned_rules.json) {
  Copy-Item data\property\learned_rules.json "data\property\backups\labels_manual_$stamp.learned_rules.json"
}
```

Copy `data/property/backups/` and `data/property/checked/` somewhere else (USB, cloud folder) if you want an off-machine copy. There is no extra database to dump.

## Restore a snapshot

Restoring `labels.db` restores **every month** in that file, not only one month.

1. Stop the Review App (uvicorn) so nothing has the DB open.
2. Pick a file in `data/property/backups/` (newest `before-run` / `before-wipe` / `manual` that you trust).
3. Copy it over the live DB, and restore rules if you have the matching JSON:

**Windows (PowerShell)** — change the snapshot name to the file you want:

```powershell
Copy-Item data\property\backups\labels_before-run_JAN2026_20261004-195800.db data\property\labels.db
Copy-Item data\property\backups\labels_before-run_JAN2026_20261004-195800.learned_rules.json data\property\learned_rules.json
```

4. Start the Review App again.

If a `labels.db-wal` or `labels.db-shm` is left over from the old session, delete those two files **after** stopping the app and **before** starting it on the restored `labels.db`.

## How not to lose a month

- Do **not** re-run `run_month` for a month you have already reviewed unless you mean to wipe that month’s labels. You will be asked to type the month code; a snapshot is taken if you proceed.
- Do **not** run `python scripts/wipe_db.py` unless you intend to empty the whole database (it snapshots first).
- After review, run `python -m property_pipeline finalize_month MMMYYYY` so `checked/MMMYYYY_codedAndCategorised.xlsx` exists. That spreadsheet is the durable monthly deliverable even if the DB is later replaced. If that file (or the matching csv) already exists, it is **renamed** first to `MMMYYYY_codedAndCategorised_bak_YYYYmmdd-HHMMSS.xlsx` (close it in Excel if rename fails).
