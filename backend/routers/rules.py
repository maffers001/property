"""CRUD for categorisation rules, including user-learned rules."""

import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from property_pipeline.db import get_db
from property_pipeline.config import DB_PATH
from property_pipeline.learned_rules import (
    delete_learned_rule,
    load_learned_rules,
    new_rule_id,
    rule_row_from_fields,
    suggest_pattern,
    suggest_pattern_from_samples,
    test_pattern,
    upsert_learned_rule,
)
from property_pipeline.pipeline import seed_db

from backend.auth import get_current_user

router = APIRouter(prefix="/api", tags=["rules"])


class RuleBody(BaseModel):
    rule_id: str | None = None
    phase: str = "override"
    pattern: str = ""
    property_code: str = ""
    category: str = ""
    subcategory: str = ""
    outputs_json: str | None = None
    strength: str = "strong"
    order_index: int = -1
    enabled: int = 1
    apply_when_json: str | None = None


class FromReviewBody(BaseModel):
    memo: str = ""
    counterparty: str = ""
    match_text: str = ""
    property_code: str = ""
    category: str = ""
    subcategory: str = ""
    pattern: str | None = None
    phase: str | None = None
    strength: str = "strong"
    exclude_tx_id: str = ""
    exclude_tx_ids: list[str] = []
    samples: list[str] = []
    limit: int = 25


def _outputs_from_row(row: dict) -> dict:
    try:
        return json.loads(row.get("outputs_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _learned_by_id() -> dict[str, dict]:
    return {r["rule_id"]: r for r in load_learned_rules() if r.get("rule_id")}


def _to_api(row: dict, learned: dict[str, dict] | set[str]) -> dict:
    out = _outputs_from_row(row)
    rid = row["rule_id"]
    meta = learned.get(rid, {}) if isinstance(learned, dict) else {}
    learned_ids = set(learned) if not isinstance(learned, dict) else set(learned)
    return {
        "rule_id": rid,
        "order_index": row.get("order_index", 0),
        "phase": row.get("phase") or "",
        "pattern": row.get("pattern") or "",
        "outputs_json": row.get("outputs_json") or "{}",
        "property_code": out.get("property_code") or "",
        "category": out.get("category") or "",
        "subcategory": out.get("subcategory") or "",
        "strength": row.get("strength") or "medium",
        "apply_when_json": row.get("apply_when_json"),
        "enabled": int(row.get("enabled") or 0),
        "learned": rid in learned_ids or str(rid).startswith("user_"),
        "created_at": meta.get("created_at") or row.get("created_at") or "",
        "updated_at": meta.get("updated_at") or row.get("updated_at") or "",
    }


def _write_db(conn, rule: dict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO rules
           (rule_id, order_index, phase, pattern, outputs_json,
            strength, apply_when_json, banks_json, accounts_json, enabled)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            rule["rule_id"],
            rule.get("order_index", -1),
            rule["phase"],
            rule["pattern"],
            rule["outputs_json"],
            rule.get("strength", "strong"),
            rule.get("apply_when_json"),
            rule.get("banks_json"),
            rule.get("accounts_json"),
            rule.get("enabled", 1),
        ),
    )


def _label_conflict(existing: str, proposed: str) -> bool:
    e = (existing or "").strip()
    p = (proposed or "").strip()
    return bool(e and p and e != p)


def _preview_other_matches(
    pattern: str,
    *,
    exclude_tx_id: str = "",
    exclude_tx_ids: list[str] | None = None,
    property_code: str = "",
    category: str = "",
    subcategory: str = "",
    limit: int = 25,
) -> dict:
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return {"other_count": 0, "conflict_count": 0, "others": []}
    limit = max(1, min(int(limit or 25), 50))
    skip = {x for x in (exclude_tx_ids or []) if x}
    if exclude_tx_id:
        skip.add(exclude_tx_id)
    others: list[dict] = []
    conflict_count = 0
    with get_db(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT c.tx_id, c.import_batch_id, c.posted_date, c.source_account, c.amount,
                   c.memo, c.match_text,
                   l.property_code, l.category, l.subcategory
            FROM transactions_canonical c
            LEFT JOIN transactions_labels l
              ON l.tx_id = c.tx_id
             AND l.label_version = (
                 SELECT MAX(label_version) FROM transactions_labels l2 WHERE l2.tx_id = c.tx_id
             )
            WHERE IFNULL(c.is_superseded, 0) = 0
            ORDER BY c.posted_date, c.tx_id
            """
        ).fetchall()
    for r in rows:
        row = dict(r)
        tx_id = row.get("tx_id") or ""
        if tx_id in skip:
            continue
        text = row.get("match_text") or row.get("memo") or ""
        try:
            if not compiled.match(text):
                continue
        except re.error:
            continue
        conflict = (
            _label_conflict(row.get("property_code") or "", property_code)
            or _label_conflict(row.get("category") or "", category)
            or _label_conflict(row.get("subcategory") or "", subcategory)
        )
        if conflict:
            conflict_count += 1
        posted = row.get("posted_date") or ""
        others.append(
            {
                "tx_id": tx_id,
                "month": row.get("import_batch_id") or "",
                "date": str(posted)[:10],
                "account": row.get("source_account") or "",
                "amount": row.get("amount"),
                "memo": row.get("memo") or "",
                "property_code": row.get("property_code") or "",
                "category": row.get("category") or "",
                "subcategory": row.get("subcategory") or "",
                "conflict": conflict,
            }
        )
    return {
        "other_count": len(others),
        "conflict_count": conflict_count,
        "others": others[:limit],
    }


def _validate_pattern(pattern: str) -> None:
    if not (pattern or "").strip():
        raise HTTPException(status_code=400, detail="Pattern required")
    try:
        re.compile(pattern)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {e}") from e


@router.get("/rules")
def list_rules(user: dict = Depends(get_current_user)):
    with get_db(DB_PATH) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM rules").fetchone()["n"]
    if int(n or 0) == 0:
        seed_db()
    learned = _learned_by_id()
    with get_db(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT * FROM rules ORDER BY phase, order_index, rule_id"
        ).fetchall()
    return [_to_api(dict(r), learned) for r in rows]


@router.post("/rules")
def create_rule(body: RuleBody, user: dict = Depends(get_current_user)):
    _validate_pattern(body.pattern)
    if body.outputs_json:
        try:
            json.loads(body.outputs_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid outputs JSON: {e}") from e
        rule = {
            "rule_id": body.rule_id or new_rule_id(),
            "order_index": body.order_index,
            "phase": body.phase,
            "pattern": body.pattern.strip(),
            "outputs_json": body.outputs_json,
            "strength": body.strength,
            "apply_when_json": body.apply_when_json,
            "banks_json": None,
            "accounts_json": None,
            "enabled": body.enabled,
        }
    else:
        rule = rule_row_from_fields(
            rule_id=body.rule_id or new_rule_id(),
            phase=body.phase,
            pattern=body.pattern.strip(),
            property_code=body.property_code,
            category=body.category,
            subcategory=body.subcategory,
            strength=body.strength,
            order_index=body.order_index,
            enabled=body.enabled,
            apply_when_json=body.apply_when_json,
        )
    upsert_learned_rule(rule)
    with get_db(DB_PATH) as conn:
        _write_db(conn, rule)
    return _to_api(rule, _learned_by_id())


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, body: RuleBody, user: dict = Depends(get_current_user)):
    _validate_pattern(body.pattern)
    with get_db(DB_PATH) as conn:
        existing = conn.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.outputs_json:
        try:
            json.loads(body.outputs_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid outputs JSON: {e}") from e
        outputs_json = body.outputs_json
    else:
        outputs_json = rule_row_from_fields(
            rule_id=rule_id,
            phase=body.phase,
            pattern=body.pattern,
            property_code=body.property_code,
            category=body.category,
            subcategory=body.subcategory,
        )["outputs_json"]
    rule = {
        "rule_id": rule_id,
        "order_index": body.order_index,
        "phase": body.phase,
        "pattern": body.pattern.strip(),
        "outputs_json": outputs_json,
        "strength": body.strength,
        "apply_when_json": body.apply_when_json,
        "banks_json": dict(existing).get("banks_json") if existing else None,
        "accounts_json": dict(existing).get("accounts_json") if existing else None,
        "enabled": body.enabled,
    }
    upsert_learned_rule(rule)
    with get_db(DB_PATH) as conn:
        _write_db(conn, rule)
    return _to_api(rule, _learned_by_id())


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, user: dict = Depends(get_current_user)):
    learned = delete_learned_rule(rule_id)
    if rule_id.startswith("user_") or learned:
        with get_db(DB_PATH) as conn:
            conn.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
        return {"ok": True, "deleted": True}
    # Built-in: disable via overlay so seed_db does not revive it as enabled
    with get_db(DB_PATH) as conn:
        existing = conn.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule = dict(existing)
    rule["enabled"] = 0
    upsert_learned_rule(rule)
    with get_db(DB_PATH) as conn:
        conn.execute("UPDATE rules SET enabled = 0 WHERE rule_id = ?", (rule_id,))
    return {"ok": True, "deleted": False, "disabled": True}


@router.post("/rules/from-review")
def rules_from_review(body: FromReviewBody, user: dict = Depends(get_current_user)):
    pattern = (body.pattern or "").strip() or suggest_pattern(
        memo=body.memo, counterparty=body.counterparty, match_text=body.match_text
    )
    _validate_pattern(pattern)
    check = test_pattern(
        pattern,
        memo=body.memo,
        counterparty=body.counterparty,
        match_text=body.match_text,
    )
    if check.get("sample") and not check.get("matched"):
        raise HTTPException(
            status_code=400,
            detail="Pattern does not match this transaction. Adjust the regex until it matches, then save.",
        )
    phase = body.phase
    if not phase:
        if (body.property_code or "").strip() and not (body.category or body.subcategory):
            phase = "property"
        else:
            phase = "override"
    created: list[dict] = []
    # Property pass only reads property_code; override reads cat/subcat
    if (body.property_code or "").strip():
        rule = rule_row_from_fields(
            phase="property",
            pattern=pattern,
            property_code=body.property_code,
            strength=body.strength,
            order_index=-1,
        )
        upsert_learned_rule(rule)
        with get_db(DB_PATH) as conn:
            _write_db(conn, rule)
        created.append(rule)
    if (body.category or "").strip() or (body.subcategory or "").strip():
        rule = rule_row_from_fields(
            phase=phase if phase != "property" else "override",
            pattern=pattern,
            category=body.category,
            subcategory=body.subcategory,
            strength=body.strength,
            order_index=-1,
        )
        upsert_learned_rule(rule)
        with get_db(DB_PATH) as conn:
            _write_db(conn, rule)
        created.append(rule)
    if not created:
        raise HTTPException(status_code=400, detail="Set at least a property, category, or subcategory")
    learned = _learned_by_id()
    return {
        "ok": True,
        "pattern": pattern,
        "rules": [_to_api(r, learned) for r in created],
    }


@router.post("/rules/test")
def rules_test_pattern(body: FromReviewBody, user: dict = Depends(get_current_user)):
    result = test_pattern(
        (body.pattern or "").strip(),
        memo=body.memo,
        counterparty=body.counterparty,
        match_text=body.match_text,
    )
    if result.get("ok") and (body.pattern or "").strip():
        preview = _preview_other_matches(
            (body.pattern or "").strip(),
            exclude_tx_id=body.exclude_tx_id,
            exclude_tx_ids=body.exclude_tx_ids,
            property_code=body.property_code,
            category=body.category,
            subcategory=body.subcategory,
            limit=body.limit,
        )
        result.update(preview)
        if body.samples:
            try:
                compiled = re.compile((body.pattern or "").strip(), re.IGNORECASE)
            except re.error:
                compiled = None
            hit = 0
            missed: list[str] = []
            if compiled is not None:
                for s in body.samples:
                    if compiled.match(s or ""):
                        hit += 1
                    else:
                        missed.append(s)
            result["selected_count"] = len(body.samples)
            result["selected_matched"] = hit
            result["selected_missed"] = missed[:8]
        else:
            result["selected_count"] = 1
            result["selected_matched"] = 1 if result.get("matched") else 0
            result["selected_missed"] = []
    else:
        result["other_count"] = 0
        result["conflict_count"] = 0
        result["others"] = []
    return result


@router.get("/rules/suggest-pattern")
def rules_suggest_pattern(
    memo: str = "",
    counterparty: str = "",
    match_text: str = "",
    user: dict = Depends(get_current_user),
):
    return {"pattern": suggest_pattern(memo=memo, counterparty=counterparty, match_text=match_text)}


class SuggestSamplesBody(BaseModel):
    samples: list[str] = []


@router.post("/rules/suggest-from-samples")
def rules_suggest_from_samples(body: SuggestSamplesBody, user: dict = Depends(get_current_user)):
    return {"pattern": suggest_pattern_from_samples(body.samples or [])}
