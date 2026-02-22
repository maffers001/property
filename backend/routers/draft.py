"""Draft and review read endpoints: months, lists, draft, review queue."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from property_pipeline.db import get_db
from property_pipeline.config import DB_PATH
from property_pipeline.rules_seed import get_categories_and_subcategories
from property_pipeline.pipeline import _load_canonical_for_month

from backend.auth import get_current_user

router = APIRouter(prefix="/api", tags=["draft"])


def _load_latest_labels_with_meta(conn, tx_ids: list[str]) -> list[dict]:
    """Load latest label per tx_id including confidence, needs_review, rule_strength, reviewed_at."""
    if not tx_ids:
        return []
    placeholders = ",".join(["?"] * len(tx_ids))
    cursor = conn.execute(
        f"""
        SELECT l.tx_id, l.property_code, l.category, l.subcategory,
               l.confidence, l.needs_review, l.rule_strength, l.reviewed_at
        FROM transactions_labels l
        INNER JOIN (
            SELECT tx_id, MAX(label_version) AS mv FROM transactions_labels
            WHERE tx_id IN ({placeholders}) GROUP BY tx_id
        ) m ON l.tx_id = m.tx_id AND l.label_version = m.mv
        WHERE l.tx_id IN ({placeholders})
        """,
        tx_ids + tx_ids,
    )
    return [dict(row) for row in cursor.fetchall()]


def _apply_filters(rows: list[dict], properties: list[str], categories: list[str],
                   subcategories: list[str], search: str | None,
                   date_from: str | None, date_to: str | None,
                   needs_review_only: bool = False) -> list[dict]:
    if not rows:
        return rows
    if properties:
        rows = [r for r in rows if (r.get("property_code") or "") in properties or (r.get("Property") or "") in properties]
    if categories:
        rows = [r for r in rows if (r.get("category") or r.get("Cat") or "") in categories]
    if subcategories:
        rows = [r for r in rows if (r.get("subcategory") or r.get("Subcat") or "") in subcategories]
    if needs_review_only:
        rows = [r for r in rows if r.get("needs_review") == 1]
    if search and search.strip():
        q = search.strip().lower()
        rows = [
            r for r in rows
            if q in (r.get("memo") or "").lower() or q in (r.get("counterparty") or "").lower()
        ]
    if date_from or date_to:
        def parse_d(s):
            if not s:
                return None
            try:
                return datetime.strptime(s[:10], "%Y-%m-%d").date()
            except Exception:
                return None
        d_from = parse_d(date_from)
        d_to = parse_d(date_to)
        def keep(r):
            ds = r.get("posted_date") or r.get("Date")
            if isinstance(ds, str):
                d = parse_d(ds)
            else:
                d = ds.date() if hasattr(ds, "date") else None
            if not d:
                return True
            if d_from and d < d_from:
                return False
            if d_to and d > d_to:
                return False
            return True
        rows = [r for r in rows if keep(r)]
    return rows


def _get(d: dict, *keys: str, default=""):
    """Get first existing key from dict (handles sqlite3.Row key casing)."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
        # try lowercase for sqlite3.Row on some systems
        k_low = k.lower()
        if k_low in d and d[k_low] is not None:
            return d[k_low]
    return default


def _canonical_and_labels_to_rows(canonical: list[dict], labels: list[dict]) -> list[dict]:
    """Merge canonical + latest labels into API row shape. Date as ISO string."""
    lab_by_tx = {lab["tx_id"]: lab for lab in labels}
    rows = []
    for c in canonical:
        tx_id = _get(c, "tx_id") or ""
        if not tx_id:
            continue
        lab = lab_by_tx.get(tx_id) or {}
        posted = _get(c, "posted_date")
        if hasattr(posted, "isoformat"):
            date_str = posted.isoformat()[:10]
        else:
            date_str = str(posted)[:10] if posted else ""
        amount_val = _get(c, "amount")
        try:
            amount_float = float(amount_val) if amount_val not in (None, "") else 0.0
        except (TypeError, ValueError):
            amount_float = 0.0
        conf = lab.get("confidence")
        if conf is not None:
            try:
                conf = float(conf)
            except (TypeError, ValueError):
                conf = None
        rows.append({
            "tx_id": tx_id,
            "Date": date_str,
            "Account": _get(c, "source_account"),
            "Amount": amount_float,
            "Subcategory": _get(c, "effective_subcategory"),
            "Memo": _get(c, "memo"),
            "Property": _get(lab, "property_code"),
            "property_code": _get(lab, "property_code"),
            "Description": _get(c, "description"),
            "Cat": _get(lab, "category"),
            "category": _get(lab, "category"),
            "Subcat": _get(lab, "subcategory"),
            "subcategory": _get(lab, "subcategory"),
            "counterparty": _get(c, "counterparty"),
            "confidence": conf,
            "needs_review": 1 if lab.get("needs_review") else 0,
            "rule_strength": _get(lab, "rule_strength"),
            "reviewed_at": _get(lab, "reviewed_at"),
        })
    return rows


@router.get("/months")
def get_months(user: dict = Depends(get_current_user)):
    with get_db(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT DISTINCT import_batch_id FROM transactions_canonical ORDER BY import_batch_id DESC"
        )
        months = [row["import_batch_id"] for row in cursor.fetchall()]
    return months


@router.get("/lists")
def get_lists(user: dict = Depends(get_current_user)):
    categories, subcategories = get_categories_and_subcategories()
    with get_db(DB_PATH) as conn:
        cursor = conn.execute("SELECT property_code FROM properties ORDER BY property_code")
        property_codes = [row["property_code"] for row in cursor.fetchall()]
        cursor = conn.execute(
            "SELECT list_type, value FROM custom_list_entries ORDER BY list_type, value"
        )
        custom = {"property": [], "category": [], "subcategory": []}
        for row in cursor.fetchall():
            t, v = row["list_type"], row["value"]
            if t in custom and v and v not in custom[t]:
                custom[t].append(v)
    # Merge custom entries (avoid duplicates, keep sorted)
    property_codes = sorted(set(property_codes) | set(custom["property"]))
    categories = sorted(set(categories) | set(custom["category"]))
    subcategories = sorted(set(subcategories) | set(custom["subcategory"]))
    return {
        "property_codes": property_codes,
        "categories": categories,
        "subcategories": subcategories,
    }


@router.get("/draft")
def get_draft(
    month: str = Query(..., description="e.g. OCT2025"),
    property_codes: str | None = Query(None, alias="property", description="Comma-separated property codes"),
    category: str | None = Query(None, description="Comma-separated categories"),
    subcategory: str | None = Query(None, description="Comma-separated subcategories"),
    search: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    format: str | None = Query(None, description="csv to get CSV response"),
    user: dict = Depends(get_current_user),
):
    properties = [p.strip() for p in (property_codes or "").split(",") if p.strip()]
    categories = [c.strip() for c in (category or "").split(",") if c.strip()]
    subcategories = [s.strip() for s in (subcategory or "").split(",") if s.strip()]

    with get_db(DB_PATH) as conn:
        canonical = _load_canonical_for_month(conn, month)
    if not canonical:
        return [] if format != "csv" else _empty_csv_response()

    tx_ids = [c["tx_id"] for c in canonical]
    with get_db(DB_PATH) as conn:
        labels = _load_latest_labels_with_meta(conn, tx_ids)

    rows = _canonical_and_labels_to_rows(canonical, labels)
    rows = _apply_filters(rows, properties, categories, subcategories, search, date_from, date_to, needs_review_only=False)

    if format == "csv":
        return _rows_to_csv_response(rows)
    return rows


@router.get("/review")
def get_review(
    month: str = Query(...),
    property_codes: str | None = Query(None, alias="property"),
    category: str | None = Query(None),
    subcategory: str | None = Query(None),
    search: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    format: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    properties = [p.strip() for p in (property_codes or "").split(",") if p.strip()]
    categories = [c.strip() for c in (category or "").split(",") if c.strip()]
    subcategories = [s.strip() for s in (subcategory or "").split(",") if s.strip()]

    with get_db(DB_PATH) as conn:
        canonical = _load_canonical_for_month(conn, month)
    if not canonical:
        return [] if format != "csv" else _empty_csv_response()

    tx_ids = [c["tx_id"] for c in canonical]
    with get_db(DB_PATH) as conn:
        labels = _load_latest_labels_with_meta(conn, tx_ids)

    rows = _canonical_and_labels_to_rows(canonical, labels)
    rows = _apply_filters(rows, properties, categories, subcategories, search, date_from, date_to, needs_review_only=True)

    if format == "csv":
        return _rows_to_csv_response(rows)
    return rows


def _empty_csv_response():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("Date,Account,Amount,Memo,Property,Cat,Subcat,tx_id,confidence,needs_review\n", media_type="text/csv")


def _rows_to_csv_response(rows: list[dict]):
    import csv
    import io
    from fastapi.responses import PlainTextResponse
    out = io.StringIO()
    if not rows:
        out.write("Date,Account,Amount,Memo,Property,Cat,Subcat,tx_id,confidence,needs_review\n")
    else:
        cols = ["Date", "Account", "Amount", "Memo", "Property", "Cat", "Subcat", "tx_id", "confidence", "needs_review"]
        w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    return PlainTextResponse(out.getvalue(), media_type="text/csv")
