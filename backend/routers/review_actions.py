"""Review write endpoints: add to review, remove from review, correct label, submit review."""
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from property_pipeline.db import get_db
from property_pipeline.config import DB_PATH
from property_pipeline.pipeline import _load_canonical_for_month
from property_pipeline import pipeline as pl

from backend.auth import get_current_user

router = APIRouter(prefix="/api", tags=["review-actions"])


def _get_latest_label(conn, tx_id: str) -> dict | None:
    cursor = conn.execute(
        """SELECT property_code, category, subcategory, needs_review, reviewed
           FROM transactions_labels
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


class SubmitBody(BaseModel):
    tx_ids: list[str] | None = None


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
    return {"ok": True, "count": len(body.tx_ids)}


class BulkCorrectBody(BaseModel):
    tx_ids: list[str]
    property_code: str = ""
    category: str = ""
    subcategory: str = ""
    pattern: str = ""


def _tx_ids_matching_pattern(pattern: str) -> list[str]:
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {e}") from e
    ids: list[str] = []
    total = 0
    with get_db(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT tx_id, match_text, memo
            FROM transactions_canonical
            WHERE IFNULL(is_superseded, 0) = 0
            """
        ).fetchall()
    for r in rows:
        total += 1
        text = r["match_text"] or r["memo"] or ""
        if compiled.match(text):
            ids.append(r["tx_id"])
    if total > 20 and len(ids) >= total:
        raise HTTPException(
            status_code=400,
            detail="Pattern matches every imported row; narrow it before applying to all matches",
        )
    return ids


@router.post("/review/correct")
def review_correct(body: CorrectBody, user: dict = Depends(get_current_user)):
    """Save Property/Cat/Subcat. Rows flagged for review stay flagged until Mark reviewed."""
    with get_db(DB_PATH) as conn:
        prev = _get_latest_label(conn, body.tx_id)
        still_in_review = 1 if (prev and prev.get("needs_review")) else 0
        _insert_label(
            conn, body.tx_id,
            body.property_code or "",
            body.category or "",
            body.subcategory or "",
            needs_review=still_in_review,
            reviewed=0 if still_in_review else 1,
        )
    return {"ok": True}


@router.post("/review/correct-bulk")
def review_correct_bulk(body: BulkCorrectBody, user: dict = Depends(get_current_user)):
    """Apply the same Property/Cat/Subcat to listed txs, and optionally every regex match."""
    ids = [x for x in body.tx_ids if x]
    if (body.pattern or "").strip():
        seen = set(ids)
        for tx_id in _tx_ids_matching_pattern(body.pattern.strip()):
            if tx_id not in seen:
                seen.add(tx_id)
                ids.append(tx_id)
    n = 0
    with get_db(DB_PATH) as conn:
        for tx_id in ids:
            if not tx_id:
                continue
            prev = _get_latest_label(conn, tx_id)
            still_in_review = 1 if (prev and prev.get("needs_review")) else 0
            _insert_label(
                conn, tx_id,
                body.property_code or "",
                body.category or "",
                body.subcategory or "",
                needs_review=still_in_review,
                reviewed=0 if still_in_review else 1,
            )
            n += 1
    return {"ok": True, "count": n}


@router.post("/review/complete")
def review_complete(body: ReviewAddRemoveBody, user: dict = Depends(get_current_user)):
    """Mark selected queue rows as reviewed (needs_review=0). Labels already saved via correct stay."""
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
                reviewed=1,
            )
    return {"ok": True, "count": len(body.tx_ids)}


@router.post("/review/submit")
def review_submit(
    month: str = Query(..., description="e.g. OCT2025"),
    body: SubmitBody | None = None,
    user: dict = Depends(get_current_user),
):
    """Mark queue rows as reviewed. If body.tx_ids is set, only those rows; otherwise all remaining for the month."""
    only_ids = set(body.tx_ids) if body and body.tx_ids else None
    with get_db(DB_PATH) as conn:
        canonical = _load_canonical_for_month(conn, month)
    if not canonical:
        return {"ok": True, "applied": 0}

    tx_ids = [c["tx_id"] for c in canonical]
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
    if only_ids is not None:
        to_submit = [row for row in to_submit if row["tx_id"] in only_ids]

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