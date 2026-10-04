# Property analytics: project summary and notes from development chat

This document is a catch-up guide: what the project is, how the current Python pipeline works, and important decisions from development chats (Phase 3, review/finalize, Excel UX, extra property-matching rules, Review App, OpenClaw skill, and VPS/seeding).

For the **monthly steps** see `documentation/PROCESS.md`. For **how to back up and restore** `labels.db` see `documentation/BACKUP.md`. For day-to-day CLI extras see `property_pipeline/README.md`. For business categories, property codes, and the old notebook flow see `PROJECT_CONTEXT.md`. OpenClaw agent instructions live in `scripts/openclaw/property-pipeline/SKILL.md`.

---

## 1. What this project is

The repo supports **property rental analytics**. Four bank accounts are combined each month into categorised transactions used for the **monthly rent statement**:

| Account | Role |
|---------|------|
| Starling business (`0055`) | Rents in, property expenses, director income |
| Barclays `3072` | Mortgage payments |
| Barclays `6045` | Personal |
| Barclays `4040` | Household |

Each transaction is given a **property code**, **category** (Cat), and **subcategory** (Subcat). The **deliverable** for the statement notebook (`3.0 MonthlySummary`) is a checked spreadsheet in `data/property/checked/`.

The old Jupyter flow (notebooks 1.0 → 1.5 → 2.0 → manual check → 3.0) is largely replaced by the **`property_pipeline`** package. Notebook 3.0 still consumes the checked file.

---

## 2. Layout and data paths

| Path | Purpose |
|------|--------|
| `data/property/bank-download/` | Monthly bank CSVs the pipeline reads |
| `data/property/bank-download/incoming/` | Drop raw downloads here, then run `scripts/preprocess_bank_downloads.py` |
| `data/property/bank-download/all_tenancies.xls` | Update on a new tenancy |
| `data/property/generated/` | Full-month coded files and diagnostics |
| `data/property/checked/` | Final month files for 3.0 MonthlySummary |
| `data/property/labels.db` | SQLite: canonical txs, labels, rules, properties |
| `data/property/learned_rules.json` | Rules saved in the Review App |
| `data/property/backups/` | Automatic copies of `labels.db` (see `documentation/BACKUP.md`) |
| `property_pipeline/` | Import, four-pass rule engine, export, CLI |
| `backend/` + `frontend/` | Optional Review App (FastAPI + React) |
| `scripts/openclaw/` | OpenClaw skill so an agent can run the pipeline |
| `scripts/preprocess_bank_downloads.py` | Split/normalise `incoming/` into monthly CSVs |
| `scripts/check_bank_downloads.py` | Poll `bank-download/` for months; `--run` only if all four files exist (skips months already in the DB unless `--yes`) |
| `scripts/wipe_db.py` | Empty all tables in `labels.db` (asks `y/N`; then VACUUM) |
| `python/PropertyAnalytics_v2/` | Original notebooks |

**Bank files per month:**

- `BC_4040_MMMYYYY.csv`
- `BC_3072_MMMYYYY.csv`
- `BC_6045_MMMYYYY.csv`
- `StarlingStatement_YYYY-MM.csv`

---

## 3. Pipeline commands (current)

From repo root, after `pip install -r requirements.txt` (includes scikit-learn and joblib for optional ML):

```bash
python -m property_pipeline seed_db
python -m property_pipeline run_month OCT2025
python -m property_pipeline run_month OCT2025 --use-ml
python -m property_pipeline run_month OCT2025 --yes   # skip confirm; still snapshots first
python -m property_pipeline finalize_month OCT2025
python -m property_pipeline load_historical
python -m property_pipeline grade_rules
python -m property_pipeline train_ml
python -m property_pipeline backtest
python scripts/check_bank_downloads.py          # list months / completeness
python scripts/check_bank_downloads.py --run    # run_month only for complete months
python scripts/wipe_db.py                       # wipe labels.db (confirm y)
```

`run_month` calls `seed_db` first, so rules/properties from `property_pipeline/rules_seed.py` are written into the DB (`INSERT OR REPLACE`). Re-running a month **clears that month’s data first** (labels, canonical, raw) then re-imports, so it is a full replace. If the month already has transactions, the CLI asks you to type the month code (or pass `--yes`). A copy of `labels.db` is written to `data/property/backups/` first.

**Polling:** `check_bank_downloads.py --run` waits until all four bank files for a month are present; incomplete months are skipped. Months already in the DB are skipped unless you pass `--yes`.

How to copy or restore the database: **`documentation/BACKUP.md`**.

---

## 4. How labelling works

1. **Importers** turn bank CSVs into canonical rows (`match_text`, amount, bank subcategory, etc.).
2. **Four-pass engine** (`property_pipeline/engine.py`): property → category → subcategory → override. Regex on `match_text` / memo. First match wins within a phase.
3. **Confidence** comes from rule **strength** (`strong` / `medium` / `weak` / `catch_all`) and, when present, **measured accuracy** in `rule_performance` after `grade_rules`.
4. **needs_review = 1** when confidence is low, the rule is catch-all, or **OurRent / PropertyExpense / Mortgage** has no property code.
5. **Optional ML** (`train_ml` → `data/property/ml_model.joblib`): only overrides catch-all or confidence below 0.85, and only if ML confidence ≥ 0.9. Regex still wins on strong matches.

Rules live in **`property_pipeline/rules_seed.py`**, not as a one-off DB edit:

- **Mortgage / DD-style property codes:** `_mortgage_map_raw` (only when subcategory looks like Direct Debit / Bill Payment / etc.).
- **Rent and expense memo codes:** `_rent_expense_map_raw` (no subcategory filter). Order matters: first match wins.

After editing `rules_seed.py`, load into the DB with `python -m property_pipeline seed_db` or by running `run_month`.

---

## 5. Review and finalize (important behavioural points)

Typical month (detail: **`documentation/PROCESS.md`**):

1. Preprocess `incoming/` → `run_month` / `check_bank_downloads.py --run` → labels in `labels.db` (and a draft in `generated/`).
2. Review App → **Review MMMYYYY** (defaults to needs-review rows). Dropdowns save immediately; optional Save as rule; Mark reviewed / Done reviewing.
3. `finalize_month MMMYYYY` → rebuilds the spreadsheet **from the DB** and writes `checked/` **and** updates `generated/`.

**Partial reviews persist** in the database. Uncheck **Needs review only** to edit a row the engine was sure about.

**Do not re-run `run_month` for a reviewed month** unless you intend to wipe that month’s labels. Confirm by typing the month code (`--yes` skips the prompt). A snapshot is written to `data/property/backups/` if `labels.db` already exists. See `BACKUP.md`.

**Review does not invent regexes** unless you use **Save as rule**. Manual labels also help `grade_rules` and `train_ml`. New seed patterns still go in `rules_seed.py`.

**Blank CSV rows:** trailing empty Barclays *and* Starling lines used to become fake transactions. Importers skip rows with no date, zero amount, and no memo/counterparty/reference/notes.

---

## 6. Generated files

| File | Meaning |
|------|---------|
| `generated/MMMYYYY_codedAndCategorised.xlsx` | Full-month snapshot (Data + Lists sheets) |
| `generated/DDCheck_MMMYYYY.csv` | Direct debits and Beals (mortgage/DD check) |
| `generated/CatCheck_MMMYYYY.csv` | All categorised rows (audit) |

XLSX extras from this work:

- **Lists** sheet: Property, Category, Subcategory lists for dropdowns. Add new values in blank rows on Lists.
- **Data** (or **Review**) is the **first** sheet; Lists is second.
- Auto-filter on all headers.
- Column widths ≈ max character length; **tx_id** not auto-sized; **memo** at 50% of max length.

CSV diagnostics do not get Excel validation.

---

## 7. Rule additions from this chat

Memo suffixes (rent/expense list), e.g.:

- `17 4-6` → F1746ALH  
- `41214` / `31214` → F41214ALH / F31214ALH  
- `7 8` → F78ALH  
- `13 16-18` → F131618ALH  
- `12 1618` → F121618ALH  

Mortgage reference numbers (`_mortgage_map_raw`):

- `560471810` → F2246ALH  
- `560471701` → F2046ALH  
- `560470708` → F2346ALH  
- `560476808` → F61618ALH  
- `560470610` → F78ALH  
- `560471505` → F1946ALH  
- `560470501` → F68ALH  

---

## 8. Review App

Web UI (`backend/` + `frontend/`) on the same SQLite DB. This is the normal review path (not a queue spreadsheet).

**Requires Python 3.13.11.** Login password is `REVIEW_APP_PASSWORD`. From repo root, Windows (avoid `--reload`; it can hang):

```bash
set REVIEW_APP_PASSWORD=yourpassword
uvicorn backend.main:app --port 8000
```

Frontend: `cd frontend && npm run dev` (http://localhost:5173, proxies `/api`).

| Page | Role |
|------|------|
| Home | Month picker, count of rows needing review, link to Review / Reports / Rules |
| Review (`/review/:month`) | All txs; **Needs review only** filter (default on); inline Property/Cat/Subcat; add/remove flag; Mark reviewed / Done reviewing; Save as rule; amount sum; CSV of current view |
| Reports | Month or date range: property summary, outgoings, personal spending |
| Rules | Edit regex categorisation rules |
| Settings | Add property / category / subcategory values (`custom_list_entries`) |

---

## 9. Seeding, VPS, OpenClaw, Contabo

**Seed the DB** before the Review App or if `labels.db` is missing/empty:

```bash
python -m property_pipeline seed_db
```

Creates `data/property/labels.db` and tables (canonical, labels, rules, properties, `custom_list_entries`, …) and seeds rules/properties. After a wipe, seed again. Until you `run_month` at least once, `/api/months` returns `[]` (Home shows “No months available” — that is OK).

**VPS 500 on `GET /api/months`:** the DB file or tables do not exist (never seeded). Seed from repo root, then restart the backend. See `backend/README.md` Deployment (VPS).

**`DATA_PATH` / `DB_PATH`:** not required if you run from repo root and data is checked in at `<project-root>/data` (defaults to `data/property/labels.db`). Set them only if cwd is not the repo or data lives elsewhere.

**OpenClaw:** `scripts/openclaw/property-pipeline/SKILL.md` — poll bank files (wait for all four), run pipeline, prompt for review, finalize, seed, wipe, reports. Copy the skill folder to `~/.openclaw/workspace/skills/`. Example repo path in the skill: `/home/openclaw/code/property`.

**Contabo:** this repo does **not** document instance ID, SSH, OS, nginx/systemd, or Docker on Contabo. From an earlier session the Review App was reached at **http://45.13.59.62:8000** (`/api/months` 500 until seed), with **OpenClaw Control** also in use on that box. Treat that IP as a hint only; confirm on the server.

---

## 10. Suggested catch-up commands

```bash
pip install -r requirements.txt
python -m property_pipeline seed_db
python scripts/preprocess_bank_downloads.py
python scripts/check_bank_downloads.py
```

Then follow `documentation/PROCESS.md` (import if complete, review in the app, `finalize_month`). For ML: `load_historical` → `grade_rules` → `train_ml` → `run_month … --use-ml`.
