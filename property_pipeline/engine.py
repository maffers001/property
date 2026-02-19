"""
Four-pass rule engine.

Pass 1 (property):  Assigns property_code from mortgage_map and rent/expense rules.
Pass 2 (category):  Assigns Cat where Cat is null (first-match-wins).
Pass 3 (subcategory): Assigns Subcat where Cat=PersonalExpense and Subcat is null.
Pass 4 (override):  Unconditionally overwrites Cat and/or Subcat.
"""

import json
import re
from typing import Any

from .config import STRENGTH_CONFIDENCE, CONFIDENCE_AUTO_ACCEPT, CONFIDENCE_FORCE_REVIEW


def _check_apply_when(conditions_json: str | None, tx: dict, labels: dict) -> bool:
    """Check whether apply_when conditions are satisfied for a transaction."""
    if not conditions_json:
        return True

    conditions = json.loads(conditions_json)
    if isinstance(conditions, dict):
        conditions = [conditions]

    for cond in conditions:
        field = cond.get("field", "")
        if "regex" in cond:
            value = _get_field_value(field, tx, labels)
            if value is None or not isinstance(value, str):
                return False
            if not re.search(cond["regex"], value, re.IGNORECASE):
                return False
        if "min" in cond or "max" in cond:
            value = _get_field_value(field, tx, labels)
            try:
                num = float(value)
            except (TypeError, ValueError):
                return False
            if "min" in cond and num < cond["min"]:
                return False
            if "max" in cond and num > cond["max"]:
                return False

    return True


def _get_field_value(field: str, tx: dict, labels: dict) -> Any:
    """Get a field value from the transaction or current labels."""
    if field == "category":
        return labels.get("category")
    if field == "subcategory":
        return labels.get("subcategory")
    if field == "property_code":
        return labels.get("property_code")
    if field == "description":
        return tx.get("description") or ""
    if field in tx:
        return tx.get(field)
    return labels.get(field)


def _matches_pattern(pattern: str, tx: dict, labels: dict) -> bool:
    """Check if the rule pattern matches the transaction.

    Special pseudo-patterns starting with '__' encode non-regex conditions
    from the notebooks (e.g. subcategory-only checks, amount sign checks).
    """
    if pattern == "__PROPERTY_NOT_EMPTY__":
        prop = labels.get("property_code") or ""
        return prop.strip() != ""
    if pattern == "__AMOUNT_POSITIVE__":
        return (tx.get("amount") or 0) > 0
    if pattern == "__AMOUNT_NEGATIVE__":
        return (tx.get("amount") or 0) < 0
    if pattern == "__CATCHALL_PERSONAL__":
        return True
    if pattern.startswith("__SUBCAT_"):
        return True

    match_text = tx.get("match_text") or tx.get("memo") or ""
    try:
        return bool(re.match(pattern, match_text, re.IGNORECASE))
    except re.error:
        return False


def run_engine(
    transactions: list[dict],
    rules: list[dict],
    properties_set: set[str] | None = None,
    rule_performance: dict[str, dict] | None = None,
) -> list[dict]:
    """Run the four-pass rule engine over a list of canonical transactions.

    Args:
        transactions: list of canonical transaction dicts
        rules: list of rule dicts (all phases, will be sorted)
        properties_set: set of valid property codes for validation
        rule_performance: optional dict rule_id -> {acc_category, acc_subcategory, acc_property}
                          used to set base confidence from measured accuracy

    Returns:
        list of label dicts, one per transaction, with keys:
            tx_id, property_code, category, subcategory, description,
            confidence, rule_id, rule_strength, needs_review, source
    """
    if properties_set is None:
        properties_set = set()

    phase_rules = {
        "property": [],
        "category": [],
        "subcategory": [],
        "override": [],
    }
    for r in rules:
        if r.get("enabled", 1) and r["phase"] in phase_rules:
            phase_rules[r["phase"]].append(r)

    for phase in phase_rules:
        phase_rules[phase].sort(key=lambda r: r["order_index"])

    results = []

    for tx in transactions:
        if tx.get("is_superseded"):
            continue

        labels = {
            "property_code": None,
            "category": None,
            "subcategory": None,
            "description": tx.get("description"),
        }
        matched_rules = []

        # Pass 1: Property
        for rule in phase_rules["property"]:
            if labels["property_code"]:
                break
            if not _check_apply_when(rule.get("apply_when_json"), tx, labels):
                continue
            if _matches_pattern(rule["pattern"], tx, labels):
                outputs = json.loads(rule["outputs_json"])
                prop = outputs.get("property_code")
                if prop and (not properties_set or prop in properties_set):
                    labels["property_code"] = prop
                    matched_rules.append(("property", rule))

        # Pass 2: Category
        for rule in phase_rules["category"]:
            if labels["category"] is not None:
                break
            if not _check_apply_when(rule.get("apply_when_json"), tx, labels):
                continue
            if _matches_pattern(rule["pattern"], tx, labels):
                outputs = json.loads(rule["outputs_json"])
                labels["category"] = outputs.get("category")
                if "description" in outputs:
                    labels["description"] = outputs["description"]
                matched_rules.append(("category", rule))

        # Pass 3: Subcategory (only when cat is PersonalExpense-like and subcat null)
        if labels["subcategory"] is None:
            for rule in phase_rules["subcategory"]:
                if labels["subcategory"] is not None:
                    break
                if not _check_apply_when(rule.get("apply_when_json"), tx, labels):
                    continue
                if _matches_pattern(rule["pattern"], tx, labels):
                    outputs = json.loads(rule["outputs_json"])
                    labels["subcategory"] = outputs.get("subcategory")
                    matched_rules.append(("subcategory", rule))

        # Pass 4: Override (unconditional, all matching rules apply in order)
        for rule in phase_rules["override"]:
            if _matches_pattern(rule["pattern"], tx, labels):
                outputs = json.loads(rule["outputs_json"])
                if "category" in outputs:
                    labels["category"] = outputs["category"]
                if "subcategory" in outputs:
                    labels["subcategory"] = outputs["subcategory"]
                if "description" in outputs:
                    labels["description"] = outputs["description"]
                matched_rules.append(("override", rule))

        # Determine confidence from the most significant rule
        best_rule = None
        best_strength = "catch_all"
        best_rule_id = None

        priority = {"strong": 0, "medium": 1, "weak": 2, "catch_all": 3}
        for _phase, rule in matched_rules:
            s = rule.get("strength", "medium")
            if priority.get(s, 3) < priority.get(best_strength, 3):
                best_strength = s
                best_rule = rule
                best_rule_id = rule.get("rule_id")

        if best_rule is None and matched_rules:
            _, best_rule = matched_rules[-1]
            best_rule_id = best_rule.get("rule_id")
            best_strength = best_rule.get("strength", "medium")

        # Base confidence: from rule_performance (measured accuracy) if available, else strength
        if rule_performance and best_rule_id and best_rule_id in rule_performance:
            perf = rule_performance[best_rule_id]
            accs = []
            if perf.get("acc_category") is not None:
                accs.append(perf["acc_category"])
            if perf.get("acc_subcategory") is not None:
                accs.append(perf["acc_subcategory"])
            if perf.get("acc_property") is not None:
                accs.append(perf["acc_property"])
            if accs:
                measured = sum(accs) / len(accs)
                strength_val = STRENGTH_CONFIDENCE.get(best_strength, 0.65)
                confidence = min(0.99, max(measured * 0.95, strength_val))
            else:
                confidence = STRENGTH_CONFIDENCE.get(best_strength, 0.65)
        else:
            confidence = STRENGTH_CONFIDENCE.get(best_strength, 0.65)

        needs_review = 0
        if confidence < CONFIDENCE_FORCE_REVIEW:
            needs_review = 1
        elif best_strength == "catch_all":
            needs_review = 1
        elif confidence < CONFIDENCE_AUTO_ACCEPT:
            needs_review = 1
        # OurRent, PropertyExpense, Mortgage require a property code; if missing, force review
        prop = (labels.get("property_code") or "").strip()
        cat = (labels.get("category") or "").strip()
        if cat in ("OurRent", "PropertyExpense", "Mortgage") and not prop:
            needs_review = 1

        results.append({
            "tx_id": tx["tx_id"],
            "property_code": labels["property_code"] or "",
            "category": labels["category"] or "",
            "subcategory": labels["subcategory"] or "",
            "description": labels.get("description") or "",
            "confidence": confidence,
            "rule_id": best_rule_id,
            "rule_strength": best_strength,
            "needs_review": needs_review,
            "source": "rule",
        })

    return results
