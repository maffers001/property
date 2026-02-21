"""Review write endpoints: add to review, remove from review, correct label, submit review."""
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from property_pipeline.db import get_db
from property_pipeline.config import DB_PATH, REVIEW_DIR
from property_pipeline.pipeline import _load_canonical_for_month
from property_pipeline.export import write_review_queue
from property_pipeline.rules_seed import get_categories_and_subcategories
from property_pipeline import pipeline as pl

from backend.auth import get_current_user

router = APIRouter(prefix="/api", tags=["review-actions"])


def _get_latest_label(conn, tx_id: str) -> dict | None:
    cursor = conn.execute(
        """SELECT property_code, category, subcategory FROM transactions_labels
           WHERE tx_id = ? ORDER BY label_version DESC LIMIT 1""",
        (tx_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _insert_label(conn, tx_id: str, property_code: str, category: str, subcategory: str,
                  needs_review: int, reviewed: int) -> None:
    cur = conn.execute(
        "SELECT MAX(label_version) AS mv FROM transactions_labels WHERE tx_id = ?",
        (tx_id,),
    )
    new_ver = (cur.fetchone()["mv"] or 0) + 1
    conn.execute(
        """INSERT INTO transactions_labels
           (tx_id, label_version, property_code, category, subcategory,
            source, confidence, rule_id, rule_strength, needs_review,
            reviewed, reviewed_at)
           VALUES (?, ?, ?, ?, ?, 'manual', 1.0, NULL, NULL, ?, ?,
                   strftime('%Y-%m-%dT%H:%M:%S','now'))""",
        (tx_id, new_ver, property_code or "", category or "", subcategory or "",
         needs_review, reviewed),
    )


class ReviewAddRemoveBody(BaseModel):
    month: str
    tx_ids: list[str]


class CorrectBody(BaseModel):
    tx_id: str
    property_code: str = ""
    category: str = ""
    subcategory: str = ""


class AddByRuleBody(BaseModel):
    month: str
    category: str | None = None
    property_empty: bool = False


@router.post("/review/add-by-rule")
def review_add_by_rule(body: AddByRuleBody, user: dict = Depends(get_current_user)):
    """Add to review all rows matching: optional category, optional property_empty (Cat in OurRent/Mortgage/PropertyExpense/BealsRent and no property)."""
    with get_db(DB_PATH) as conn:
        canonical = _load_canonical_for_month(conn, body.month)
    if not canonical:
        return {"ok": True, "count": 0}
    tx_ids = [c["tx_id"] for c in canonical]
    from backend.routers.draft import _load_latest_labels_with_meta
    with get_db(DB_PATH) as conn:
        labels = _load_latest_labels_with_meta(conn, tx_ids)
    lab_by = {l["tx_id"]: l for l in labels}
    must_review_cats = {"OurRent", "Mortgage", "PropertyExpense", "BealsRent"}
    tx_ids_to_add = []
    for c in canonical:
        tx_id = c["tx_id"]
        lab = lab_by.get(tx_id) or {}
        if body.category and (lab.get("category") or "") != body.category:
            continue
        if body.property_empty:
            if (lab.get("category") or "") not in must_review_cats:
                continue
            if (lab.get("property_code") or "").strip():
                continue
        tx_ids_to_add.append(tx_id)
    if not tx_ids_to_add:
        return {"ok": True, "count": 0}
    with get_db(DB_PATH) as conn:
        for tx_id in tx_ids_to_add:
            lab = _get_latest_label(conn, tx_id)
            if not lab:
                continue
            _insert_label(
                conn, tx_id,
                lab.get("property_code") or "",
                lab.get("category") or "",
                lab.get("subcategory") or "",
                needs_review=1,
                reviewed=0,
            )
    return {"ok": True, "count": len(tx_ids_to_add)}


@router.post("/review/add")
def review_add(body: ReviewAddRemoveBody, user: dict = Depends(get_current_user)):
    """Add given tx_ids to review (set needs_review=1, keep current labels)."""
    with get_db(DB_PATH) as conn:
        for tx_id in body.tx_ids:
            if not tx_id:
                continue
            lab = _get_latest_label(conn, tx_id)
            if not lab:
                continue
            _insert_label(
                conn, tx_id,
                lab.get("property_code") or "",
                lab.get("category") or "",
                lab.get("subcategory") or "",
                needs_review=1,
                reviewed=0,
            )
    _write_review_queue_for_month(body.month)
    return {"ok": True, "count": len(body.tx_ids)}


@router.post("/review/remove")
def review_remove(body: ReviewAddRemoveBody, user: dict = Depends(get_current_user)):
    """Remove given tx_ids from review (set needs_review=0)."""
    with get_db(DB_PATH) as conn:
        for tx_id in body.tx_ids:
            if not tx_id:
                continue
            lab = _get_latest_label(conn, tx_id)
            if not lab:
                continue
            _insert_label(
                conn, tx_id,
                lab.get("property_code") or "",
                lab.get("category") or "",
                lab.get("subcategory") or "",
                needs_review=0,
                reviewed=0,
            )
    _write_review_queue_for_month(body.month)
    return {"ok": True, "count": len(body.tx_ids)}


def _write_review_queue_for_month(month: str) -> None:
    """Update review_queue_MMMYYYY.xlsx from current DB so spreadsheet reflects partial progress."""
    try:
        with get_db(DB_PATH) as conn:
            canonical = _load_canonical_for_month(conn, month)
        if not canonical:
            return
        tx_ids = [c["tx_id"] for c in canonical]
        from backend.routers.draft import _load_latest_labels_with_meta
        with get_db(DB_PATH) as conn:
            labels = _load_latest_labels_with_meta(conn, tx_ids)
        categories, subcategories = get_categories_and_subcategories()
        with get_db(DB_PATH) as conn:
            from property_pipeline.pipeline import _load_properties_set
            props = sorted(_load_properties_set(conn))
        review_path = REVIEW_DIR / f"review_queue_{month}.xlsx"
        write_review_queue(
            canonical,
            labels,
            review_path,
            property_codes=props,
            categories=categories,
            subcategories=subcategories,
        )
    except Exception:
        pass


@router.post("/review/correct")
def review_correct(body: CorrectBody, user: dict = Depends(get_current_user)):
    """Apply a single correction (new manual label, reviewed=1, needs_review=0). Persisted to DB immediately.
    The review queue spreadsheet is updated so it shows remaining items (partial progress) when you come back later."""
    with get_db(DB_PATH) as conn:
        _insert_label(
            conn, body.tx_id,
            body.property_code or "",
            body.category or "",
            body.subcategory or "",
            needs_review=0,
            reviewed=1,
        )
        cur = conn.execute(
            "SELECT import_batch_id FROM transactions_canonical WHERE tx_id = ?", (body.tx_id,)
        )
        row = cur.fetchone()
        month = row["import_batch_id"] if row else None
    if month:
        _write_review_queue_for_month(month)
    return {"ok": True}


@router.post("/review/submit")
def review_submit(
    month: str = Query(..., description="e.g. OCT2025"),
    user: dict = Depends(get_current_user),
):
    """Apply submit: for all rows in review for this month, write new label with reviewed=1, needs_review=0. Optionally update review queue XLSX."""
    with get_db(DB_PATH) as conn:
        canonical = _load_canonical_for_month(conn, month)
    if not canonical:
        return {"ok": True, "applied": 0}

    tx_ids = [c["tx_id"] for c in canonical]
    # Get latest label per tx_id and find those with needs_review=1
    with get_db(DB_PATH) as conn:
        cursor = conn.execute(
            """SELECT l.tx_id, l.property_code, l.category, l.subcategory, l.needs_review
               FROM transactions_labels l
               INNER JOIN (
                 SELECT tx_id, MAX(label_version) AS mv FROM transactions_labels
                 WHERE tx_id IN (""" + ",".join("?" * len(tx_ids)) + """) GROUP BY tx_id
               ) m ON l.tx_id = m.tx_id AND l.label_version = m.mv
               WHERE l.tx_id IN (""" + ",".join("?" * len(tx_ids)) + """) AND l.needs_review = 1""",
            tx_ids + tx_ids,
        )
        to_submit = [dict(row) for row in cursor.fetchall()]

    with get_db(DB_PATH) as conn:
        for row in to_submit:
            _insert_label(
                conn, row["tx_id"],
                row.get("property_code") or "",
                row.get("category") or "",
                row.get("subcategory") or "",
                needs_review=0,
                reviewed=1,
            )

    # Write review queue XLSX from current DB state (remaining needs_review=1 rows) so CLI stays in sync
    try:
        with get_db(DB_PATH) as conn:
            canonical = _load_canonical_for_month(conn, month)
        if canonical:
            tx_ids = [c["tx_id"] for c in canonical]
            from backend.routers.draft import _load_latest_labels_with_meta
            with get_db(DB_PATH) as conn:
                labels = _load_latest_labels_with_meta(conn, tx_ids)
            categories, subcategories = get_categories_and_subcategories()
            with get_db(DB_PATH) as conn:
                from property_pipeline.pipeline import _load_properties_set
                props = sorted(_load_properties_set(conn))
            review_path = REVIEW_DIR / f"review_queue_{month}.xlsx"
            write_review_queue(
                canonical,
                labels,
                review_path,
                property_codes=props,
                categories=categories,
                subcategories=subcategories,
            )
    except Exception:
        pass  # non-fatal: submit already applied to DB

    return {"ok": True, "applied": len(to_submit)}


@router.post("/finalize")
def finalize_month(
    month: str = Query(..., description="e.g. OCT2025"),
    user: dict = Depends(get_current_user),
):
    """Build finalized output from DB and write to checked/ and update generated/."""
    try:
        path = pl.finalize_month(month, db_path=DB_PATH)
        return {"ok": True, "path": str(path)}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))