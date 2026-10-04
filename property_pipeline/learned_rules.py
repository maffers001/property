"""User-learned rules persisted as JSON so they survive seed_db and wipe+reseed."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import LEARNED_RULES_PATH

PHASES = ("property", "category", "subcategory", "override")
STRENGTHS = ("strong", "medium", "weak", "catch_all")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(path: Path | str | None = None) -> Path:
    return Path(path) if path else LEARNED_RULES_PATH


def load_learned_rules(path: Path | str | None = None) -> list[dict]:
    p = _path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = data.get("rules") or []
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict) and r.get("rule_id")]


def save_learned_rules(rules: list[dict], path: Path | str | None = None) -> None:
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"rules": rules}, indent=2) + "\n", encoding="utf-8")


def suggest_pattern(memo: str = "", counterparty: str = "", match_text: str = "") -> str:
    """Build a regex that matches the engine sample (re.match, IGNORECASE).

    Whitespace in bank memos is irregular, so tokens are joined with \\s+.
    """
    raw = sample_match_text(memo=memo, counterparty=counterparty, match_text=match_text)
    tokens = [t for t in re.split(r"\s+", raw) if t]
    if not tokens:
        return ".*"
    chosen: list[str] = []
    n = 0
    for t in tokens:
        extra = len(t) + (1 if chosen else 0)
        if chosen and n + extra > 80:
            break
        chosen.append(re.escape(t))
        n += extra
    return ".*" + r"\s+".join(chosen) + ".*"


def suggest_pattern_from_samples(texts: list[str]) -> str:
    """Suggest a regex that should match all given match/memo texts."""
    token_lists: list[list[str]] = []
    for t in texts:
        raw = sample_match_text(match_text=t, memo=t)
        toks = [x for x in re.split(r"\s+", raw) if x]
        if toks:
            token_lists.append(toks)
    if not token_lists:
        return ".*"
    if len(token_lists) == 1:
        return suggest_pattern(match_text=" ".join(token_lists[0]))

    prefix: list[str] = []
    for parts in zip(*token_lists):
        if all(p.lower() == parts[0].lower() for p in parts):
            prefix.append(re.escape(parts[0]))
        else:
            break
    if prefix:
        return ".*" + r"\s+".join(prefix) + ".*"

    sets = [set(t.lower() for t in tl) for tl in token_lists]
    shared = sets[0].intersection(*sets[1:])
    shared = {s for s in shared if len(s) >= 3 and not re.fullmatch(r"[0-9./\\-]+", s)}
    chosen: list[str] = []
    for t in token_lists[0]:
        key = t.lower()
        if key in shared:
            chosen.append(re.escape(t))
            shared.discard(key)
        if sum(len(x) for x in chosen) > 60:
            break
    if chosen:
        return ".*" + r"\s+".join(chosen) + ".*"
    return ".*" + re.escape(token_lists[0][0]) + ".*"


def sample_match_text(memo: str = "", counterparty: str = "", match_text: str = "") -> str:
    """Same text the engine matches: match_text, else counterparty, else memo."""
    return (match_text or counterparty or memo or "").strip()


def test_pattern(
    pattern: str,
    memo: str = "",
    counterparty: str = "",
    match_text: str = "",
) -> dict:
    """Test a pattern the same way the engine does (re.match, IGNORECASE)."""
    sample = sample_match_text(memo=memo, counterparty=counterparty, match_text=match_text)
    if not (pattern or "").strip():
        return {"ok": False, "matched": False, "sample": sample, "error": "Pattern required"}
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"ok": False, "matched": False, "sample": sample, "error": f"Invalid regex: {e}"}
    matched = bool(compiled.match(sample))
    return {"ok": True, "matched": matched, "sample": sample, "error": None}


def new_rule_id() -> str:
    return "user_" + uuid.uuid4().hex[:12]


def upsert_learned_rule(rule: dict, path: Path | str | None = None) -> dict:
    rules = load_learned_rules(path)
    rid = rule["rule_id"]
    now = _now_iso()
    found = False
    for i, existing in enumerate(rules):
        if existing.get("rule_id") == rid:
            rule["created_at"] = existing.get("created_at") or now
            rule["updated_at"] = now
            rules[i] = rule
            found = True
            break
    if not found:
        rule["created_at"] = now
        rule["updated_at"] = now
        rules.append(rule)
    save_learned_rules(rules, path)
    return rule


def delete_learned_rule(rule_id: str, path: Path | str | None = None) -> bool:
    rules = load_learned_rules(path)
    next_rules = [r for r in rules if r.get("rule_id") != rule_id]
    if len(next_rules) == len(rules):
        return False
    save_learned_rules(next_rules, path)
    return True


def rule_row_from_fields(
    *,
    rule_id: str | None = None,
    phase: str,
    pattern: str,
    property_code: str = "",
    category: str = "",
    subcategory: str = "",
    strength: str = "strong",
    order_index: int = -1,
    enabled: int = 1,
    apply_when_json: str | None = None,
) -> dict:
    phase = phase if phase in PHASES else "override"
    strength = strength if strength in STRENGTHS else "strong"
    outputs: dict[str, str] = {}
    if property_code.strip():
        outputs["property_code"] = property_code.strip()
    if category.strip():
        outputs["category"] = category.strip()
    if subcategory.strip():
        outputs["subcategory"] = subcategory.strip()
    return {
        "rule_id": rule_id or new_rule_id(),
        "order_index": int(order_index),
        "phase": phase,
        "pattern": pattern,
        "outputs_json": json.dumps(outputs),
        "strength": strength,
        "apply_when_json": apply_when_json,
        "banks_json": None,
        "accounts_json": None,
        "enabled": 1 if enabled else 0,
    }
