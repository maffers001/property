# Property analytics: project summary and notes from development chat

This document is a catch-up guide: what the project is, how the current Python pipeline works, and important decisions from development chats (Phase 3, review/finalize, Excel UX, extra property-matching rules, Review App, OpenClaw skill, and VPS/seeding).

For day-to-day commands see `property_pipeline/README.md`. For business categories, property codes, and the old notebook flow see `PROJECT_CONTEXT.md`. OpenClaw agent instructions live in `scripts/openclaw/property-pipeline/SKILL.md`.

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
| `data/property/bank-download/` | Bank CSVs (inputs) |
| `data/property/generated/` | Draft outputs + diagnostics |
| `data/property/review/` | Review queue XLSX |
| `data/property/checked/` | Final files after review |
| `data/property/labels.db` | SQLite: canonical txs, labels, rules, properties |
| `property_pipeline/` | Import, four-pass rule engine, export, CLI |
| `backend/` + `frontend/` | Optional Review App (FastAPI + React) |
| `scripts/openclaw/` | OpenClaw skill so an agent can run the pipeline |
| `scripts/check_bank_downloads.py` | Poll `bank-download/` for months; `--run` only if all four files exist |
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
python -m property_pipeline review_month OCT2025
python -m property_pipeline finalize_month OCT2025
python -m property_pipeline load_historical
python -m property_pipeline grade_rules
python -m property_pipeline train_ml
python -m property_pipeline backtest
python scripts/check_bank_downloads.py          # list months / completeness
python scripts/check_bank_downloads.py --run    # run_month only for complete months
python scripts/wipe_db.py                       # wipe labels.db (confirm y)
```

`run_month` calls `seed_db` first, so rules/properties from `property_pipeline/rules_seed.py` are written into the DB (`INSERT OR REPLACE`). Re-running a month **clears that month’s data first** (labels, canonical, raw) then re-imports, so it is a full replace.

**Polling:** `check_bank_downloads.py --run` waits until all four bank files for a month are present; incomplete months are skipped.

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

Typical month:

1. `run_month MMMYYYY` → draft in `generated/`, queue in `review/review_queue_MMMYYYY.xlsx`.
2. Edit property / category / subcategory in the queue (Excel or Review App).
3. `review_month MMMYYYY` → new **manual** label versions in `transactions_labels` (needed if you edited the XLSX in Excel).
4. `finalize_month MMMYYYY` → rebuilds the spreadsheet **from the DB** (latest label per transaction) and writes `checked/` **and** updates `generated/` so they match.

**Partial reviews persist.** Inline corrections in the Review App write a new label immediately (`reviewed=1`, `needs_review=0`). Add/remove from review and each correct also rewrite `review/review_queue_MMMYYYY.xlsx` so it contains only remaining `needs_review=1` rows. You can stop and resume later; the app and the spreadsheet stay in sync. If the queue becomes empty, the export may skip writing a new file, so the last XLSX can still hold old rows until you finalize.

**Corrections not in the queue:** add a row to the review XLSX with at least `tx_id`, `property_code`, `category`, `subcategory`, then run `review_month`. The command applies **every row in the file**.

**`review_month` is not idempotent:** every run inserts a new label version for every row, even if nothing changed. Re-run only after real edits.

**Review does not invent regexes.** Manual labels help `grade_rules` and `train_ml`. New merchant/memo patterns must be added in `rules_seed.py`.

**Blank CSV rows:** trailing empty Barclays *and* Starling lines used to become fake transactions. Importers skip rows with no date, zero amount, and no memo/counterparty/reference/notes.

**Excel file locked:** if `review_queue_*.xlsx` is open in Excel, Windows raises Permission denied. Close the file and re-run.

---

## 6. Generated files

| File | Meaning |
|------|---------|
| `generated/MMMYYYY_codedAndCategorised.xlsx` | Main draft (Data + Lists sheets) |
| `review/review_queue_MMMYYYY.xlsx` | Rows flagged for review |
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

## 8. Optional Review App

Web UI (`backend/` + `frontend/`) on the same SQLite DB and files as the pipeline (alternative to editing the queue XLSX in Excel).

**Requires Python 3.13.11.** Login password is `REVIEW_APP_PASSWORD`. Backend: `uvicorn backend.main:app --reload --port 8000` from repo root. Frontend: `cd frontend && npm run dev` (usually http://localhost:5173, proxies `/api`).

| Page | Role |
|------|------|
| Home | Month picker, count of rows needing review, links to Draft / Queue / Reports |
| Draft (`/review/:month`) | All txs; filters; inline Property/Cat/Subcat dropdowns (save on change); add/remove review; submit; amount sum; CSV download |
| Queue (`/review/:month/queue`) | Only `needs_review=1`; same editing; correcting a row drops it from the queue and updates the XLSX |
| Reports | Month or date range: property summary, outgoings, personal spending (same idea as 3.0 MonthlySummary) |
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
python scripts/check_bank_downloads.py
python -m property_pipeline run_month MMMYYYY
```

Then review the queue, `review_month`, `finalize_month`. For ML: `load_historical` → `grade_rules` → `train_ml` → `run_month … --use-ml`.
