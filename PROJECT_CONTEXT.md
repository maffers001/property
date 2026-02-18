# Property Rental Analytics – Project Context

This document captures the business context, data flow, and rules for the property rental analytics pipeline. Use it (and the Cursor rules in `.cursor/rules/`) to retain context for development and automation.

---

## 1. Business setup

- **Starling business account** (first four digits **0055**): rents in, expenses out, small director income. Main trading account.
- **Joint personal account** (**3072**): mortgage payments for the flats (separate from business account for incorporation reasons).
- **Personal account** (**6045**) and **household account** (**4040**): personal/household spending; both are tracked in the monthly report.

---

## 2. Repository layout

| Path | Purpose |
|------|--------|
| `data/property/bank-download/` | Downloaded bank CSVs (inputs). |
| `data/property/generated/` | Pipeline outputs: `MMMYYYY.csv`, `MMMYYYY_coded.csv`, `MMMYYYY_codedAndCategorised.csv`. |
| `data/property/checked/` | **Final checked** files: copy of `_codedAndCategorised` after manual review, saved as `.xlsx` for the monthly statement. |
| `python/PropertyAnalytics_v2/` | Jupyter notebooks and pipeline code. |
| `data/property/bank-download/all_tenancies.xls` | Master tenancy list; updated when new tenancies start (and previous tenant end dates added). |

Paths in notebooks may reference a NAS drive (`J://...`); the canonical project layout uses the repo paths above.

---

## 3. Bank file naming convention

Per month, four files are expected in `data/property/bank-download/`:

- `BC_4040_MMMYYYY.csv` (e.g. `BC_4040_NOV2025.csv`)
- `BC_3072_MMMYYYY.csv`
- `BC_6045_MMMYYYY.csv`
- `StarlingStatement_YYYY-MM.csv` (e.g. `StarlingStatement_2025-11.csv`)

---

## 4. Pipeline (three stages + manual check + statement)

1. **1.0 CreateStandardFilesFromBankDownload (RSA Capital).ipynb**  
   - Set start/end dates at top; run all.  
   - Reads the four bank files for that month → writes **one** file: `generated/MMMYYYY.csv` (all accounts, date ascending).

2. **1.5 PopulatePropertyIds.ipynb**  
   - Set start/end dates; run all.  
   - Input: `generated/MMMYYYY.csv`.  
   - Output: `generated/MMMYYYY_coded.csv` with a **Property** column populated by text/regex rules (property list and codes live in this notebook).

3. **2.0 CategoriseFiles.ipynb**  
   - Set start/end dates; run all.  
   - Input: `generated/MMMYYYY_coded.csv`.  
   - Output: `generated/MMMYYYY_codedAndCategorised.csv` with **Cat**, **Description**, **Subcat** populated by pattern rules.

4. **Manual check (critical)**  
   - Copy `MMMYYYY_codedAndCategorised.csv` to `checked/`.  
   - Open, save as `.xlsx`, add filters.  
   - Review and correct categories, property codes, splits (e.g. new tenancy rent + agent fee).  
   - **Deliverable:** `checked/MMMYYYY_codedAndCategorised.xlsx` (or equivalent checked `.xlsx`).

5. **3.0 MonthlySummary MMMYY.ipynb**  
   - Duplicate previous month’s notebook and rename (e.g. `3.0 MonthlySummary NOV25.ipynb`).  
   - Reads from `checked/` (the checked `.xlsx`/spreadsheet).  
   - Produces rent statement and financial summary; add markdown notes for the month.

6. **all_tenancies.xls**  
   - When a new tenancy starts: add a row and set end date for the previous tenant at that property (check emails if end date unknown).

---

## 5. Category and coding rules (manual check + automation)

### Categories (Cat)

- **Mortgage** – mortgage payments; every flat has at least one (some two). Each must have a **Property** code.
- **OurRent** – rent received from tenants; all should have a property code. Letting agents: Fox & Sons, Bernards, Beals.
- **BealsRent** – rent from properties managed by Beals.
- **PropertyExpense** – property-related costs; must have a property code.  
  - **Premier Accountancy** (accountant) → use property code **RSA** (company cost).
- **ServiceCharge** – payments to freehold/block accounts (see Freehold blocks below).
- **PersonalExpense** – non-business (e.g. household from 4040). Assign **Subcat** per notebook/previous months; use **Other** when no clear subcategory.
- **OtherExpense** – if property-related → set Cat to **PropertyExpense** and set Property; if personal → **PersonalExpense**.
- **OtherIncome** – e.g. **SSE SOUTHERN** (property electricity refund) → Cat **PropertyExpense**; **PNET** (broadband) → **RegularPayment**.
- **OurRent** – **Lordswood Estates** → Cat **ServiceCharge**; fill missing property codes where possible.
- **RegularPayment** – household direct debits (mobile, insurance, etc.).
- **Funds4040** – transfer from 6045 → 4040 (household).
- **Funds6045** – transfer from 4040 → 6045.
- **Hilltop** – transfer to in-laws for utility bills.
- **Interbank** – money into 3072 (mortgages) or 4040 (household) from Starling. **MortgageRefund** – corresponding outflow from Starling.
- **MTPayment** – salary (Lloyds 1585) transferred into 6045/4040.

### Property code rules

- A transaction with a **Property** code is usually **Mortgage**, **PropertyExpense**, or **OurRent**. If it’s **PersonalExpense** with a property code, treat as likely **error** and correct.
- Use **Memo** (and prior months) to infer property: e.g. “Central Energy South Limited 464 161618 taps” → Flat 16, 16-18 Alhambra Rd → **F161618ALH**.
- If **Mortgage**, **OurRent**, **BealsRent**, or **PropertyExpense** has no property code and it cannot be resolved, flag for the user; learn from corrections for future months.

### Freehold blocks (separate accounts; not Starling business)

Block expenses must **not** be left on the Starling business account; they belong in separate freehold accounts.

- **4-6, 8, 12-14, 16-18 Alhambra Road** – Alhambra Road Management Ltd  
- **23 Hampshire Terrace** – Lordswood Estates Ltd  
- **169 Fawcett Road, 171 Fawcett Road, 321 London Road** – V.T. Estates Ltd  
- **163 Fratton Road** – Fratton Road Ltd  

### New tenancies

- Single net rent transaction (often lower due to agent fees): **split into two rows** (rent + letting agent fee), **both highlighted yellow**.
- First row: rent; Memo e.g. `Rent for period DD/MM/YY-DD/MM/YY Mr Firstname Lastname`.
- Second row: letting agent name (fee).
- Sum of the two = original transaction. Example: SEP2025, 05/09/2025 – £875 rent and £-700 agent fee (replacing single £175 net).

### Highlighting in the checked spreadsheet

- **Yellow** – best-guess Cat/Subcat or property code; or split new-tenancy rows (rent + agent fee).
- **Red** – unusual items: large personal expense, missing rent, unpaid mortgage, other anomalies.

---

## 6. Automation and modernisation goals

- Poll `data/property/bank-download/` for new bank files; run categorisation pipeline; verify categorisation and produce a monthly statement for review.
- Consolidate/streamline the three notebooks into a single, simple process where possible.
- Reduce manual categorisation (more rules/heuristics); **manual check of the final checked spreadsheet remains required**.
- Automated checks: unpaid rents, unpaid mortgages, large or unusual transactions; add notes to the monthly statement.
- WhatsApp: short summary message (total rents, mortgages, expenses; notable events; warnings for unpaid mortgages/rents, large expenses).
- If **Mortgage**, **OurRent**, **BealsRent**, or **PropertyExpense** cannot be assigned a property code, report to user and use feedback to improve next run.
- Consider hosting the checked sheets (e.g. Jupyter/notebooks or reports) behind a secure link for access.
- Future: backtest on existing months (e.g. October 2025) to match behaviour of `OCT2025_codedAndCategorised.xlsx`; later, version and commit code to GitHub.

---

## 7. Backtest reference

- Use **October 2025** files to validate pipeline and categorisation against `OCT2025_codedAndCategorised.xlsx`.
- **SEP2025_codedAndCategorised.xlsx** – example of new tenancy split (05/09/2025: £875 rent + £-700 agent fee).

---

## 8. Known issues

- Some **NOV25** mortgages could not be allocated property codes because the mortgage company changed transaction references; user to confirm references with lender and then update mapping for future months.
