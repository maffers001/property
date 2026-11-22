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


class SplitTenancyBody(BaseModel):
    tx_id: str
    property_code: str
    rent_amount: float
    fee_amount: float | None = None  # positive fees charged; stored as negative expense
    rent_memo: str = ""
    fee_memo: str = "Fox & Sons"


class UnsplitTenancyBody(BaseModel):
    tx_id: str  # original (parent) tx_id


def _money(x: float) -> float:
    return round(float(x), 2)


@router.post("/review/split-tenancy")
def review_split_tenancy(body: SplitTenancyBody, user: dict = Depends(get_current_user)):
    """Replace a net agent payment with OurRent + PropertyExpense split rows.

    Original row is superseded (hidden). Children sum to the original amount.
    Reminder: update data/property/bank-download/all_tenancies.xls for the new tenancy.
    Re-running the month clears splits until you finalize.
    """
    tx_id = (body.tx_id or "").strip()
    property_code = (body.property_code or "").strip()
    if not tx_id:
        raise HTTPException(status_code=400, detail="tx_id required")
    if not property_code:
        raise HTTPException(status_code=400, detail="property_code required")

    rent = _money(body.rent_amount)
    if rent <= 0:
        raise HTTPException(status_code=400, detail="rent_amount must be positive (gross rent)")

    with get_db(DB_PATH) as conn:
        raw = conn.execute(
            "SELECT * FROM transactions_canonical WHERE tx_id = ?", (tx_id,)
        ).fetchone()
        if not raw:
            raise HTTPException(status_code=404, detail="Transaction not found")
        parent = dict(raw)
        if int(parent.get("is_superseded") or 0) == 1:
            raise HTTPException(status_code=400, detail="Transaction is already superseded")
        if parent.get("parent_tx_id"):
            raise HTTPException(status_code=400, detail="Cannot split a row that is already a split child")

        existing = conn.execute(
            "SELECT tx_id FROM transactions_canonical WHERE parent_tx_id = ? LIMIT 1",
            (tx_id,),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This transaction already has split children; unsplit first",
            )

        net = _money(parent.get("amount") or 0)
        if body.fee_amount is None:
            fee_out = _money(rent - net)  # positive fees charged
        else:
            fee_out = _money(body.fee_amount)
        if fee_out < 0:
            raise HTTPException(status_code=400, detail="fee_amount must be >= 0 (fees charged)")

        fee_signed = _money(-fee_out)
        if abs(_money(rent + fee_signed) - net) > 0.011:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Rent ({rent}) + fee ({fee_signed}) must equal net bank amount ({net})"
                ),
            )

        rent_id = f"{tx_id}_split_1"
        fee_id = f"{tx_id}_split_2"
        rent_memo = (body.rent_memo or "").strip() or (
            f"Rent received ({property_code})"
        )
        fee_memo = (body.fee_memo or "").strip() or "Fox & Sons"

        def _child(child_id: str, amount: float, memo: str) -> dict:
            return {
                "tx_id": child_id,
                "raw_row_id": None,
                "import_batch_id": parent["import_batch_id"],
                "source_bank": parent.get("source_bank") or "",
                "source_account": parent.get("source_account") or "",
                "posted_date": parent.get("posted_date") or "",
                "amount": amount,
                "currency": parent.get("currency") or "GBP",
                "counterparty": parent.get("counterparty"),
                "reference": parent.get("reference"),
                "memo": memo,
                "type": parent.get("type"),
                "balance": parent.get("balance"),
                "bank_txn_number": parent.get("bank_txn_number"),
                "bank_category": parent.get("bank_category"),
                "bank_subcategory": parent.get("bank_subcategory"),
                "effective_subcategory": parent.get("effective_subcategory"),
                "match_text": memo,
                "description": parent.get("description"),
                "parent_tx_id": tx_id,
                "is_superseded": 0,
            }

        cols = [
            "tx_id", "raw_row_id", "import_batch_id", "source_bank",
            "source_account", "posted_date", "amount", "currency",
            "counterparty", "reference", "memo", "type", "balance",
            "bank_txn_number", "bank_category", "bank_subcategory",
            "effective_subcategory", "match_text", "description",
            "parent_tx_id", "is_superseded",
        ]
        for child in (_child(rent_id, rent, rent_memo), _child(fee_id, fee_signed, fee_memo)):
            conn.execute(
                f"INSERT INTO transactions_canonical ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' * len(cols))})",
                tuple(child.get(c) for c in cols),
            )

        conn.execute(
            "UPDATE transactions_canonical SET is_superseded = 1 WHERE tx_id = ?",
            (tx_id,),
        )

        _insert_label(
            conn, rent_id, property_code, "OurRent", "",
            needs_review=1, reviewed=0,
        )
        _insert_label(
            conn, fee_id, property_code, "PropertyExpense", "",
            needs_review=1, reviewed=0,
        )

        # Drop original from review queue visually (still in DB as superseded).
        prev = _get_latest_label(conn, tx_id)
        if prev:
            _insert_label(
                conn, tx_id,
                prev.get("property_code") or "",
                prev.get("category") or "",
                prev.get("subcategory") or "",
                needs_review=0,
                reviewed=1,
            )

    return {
        "ok": True,
        "parent_tx_id": tx_id,
        "rent_tx_id": rent_id,
        "fee_tx_id": fee_id,
        "rent_amount": rent,
        "fee_amount": fee_signed,
        "net_amount": net,
        "property_code": property_code,
        "reminder": (
            "Update data/property/bank-download/all_tenancies.xls "
            "(add new tenant; set previous tenant end date). "
            "Re-running the month will clear this split until you finalize."
        ),
    }


@router.post("/review/unsplit-tenancy")
def review_unsplit_tenancy(body: UnsplitTenancyBody, user: dict = Depends(get_current_user)):
    """Undo a tenancy split: delete child rows and restore the original."""
    tx_id = (body.tx_id or "").strip()
    if not tx_id:
        raise HTTPException(status_code=400, detail="tx_id required")

    with get_db(DB_PATH) as conn:
        parent = conn.execute(
            "SELECT * FROM transactions_canonical WHERE tx_id = ?", (tx_id,)
        ).fetchone()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent transaction not found")
        parent = dict(parent)

        children = [
            dict(r)
            for r in conn.execute(
                "SELECT tx_id FROM transactions_canonical WHERE parent_tx_id = ?",
                (tx_id,),
            ).fetchall()
        ]
        if not children:
            raise HTTPException(status_code=400, detail="No split children found for this transaction")

        child_ids = [c["tx_id"] for c in children]
        placeholders = ",".join("?" * len(child_ids))
        conn.execute(
            f"DELETE FROM transactions_labels WHERE tx_id IN ({placeholders})",
            child_ids,
        )
        conn.execute(
            f"DELETE FROM transactions_canonical WHERE tx_id IN ({placeholders})",
            child_ids,
        )
        conn.execute(
            "UPDATE transactions_canonical SET is_superseded = 0 WHERE tx_id = ?",
            (tx_id,),
        )
        prev = _get_latest_label(conn, tx_id)
        if prev:
            _insert_label(
                conn, tx_id,
                prev.get("property_code") or "",
                prev.get("category") or "",
                prev.get("subcategory") or "",
                needs_review=1,
                reviewed=0,
            )
        else:
            _insert_label(conn, tx_id, "", "", "", needs_review=1, reviewed=0)

    return {"ok": True, "parent_tx_id": tx_id, "removed": child_ids}


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