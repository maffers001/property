"""
Optional ML model: suggests category, subcategory, property_code from transaction features.
Trained on historical labels in the DB; regex keeps precedence at inference.
"""

from pathlib import Path
import sqlite3
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib

from .config import DB_PATH, MODEL_PATH
from .db import get_db


def _get_training_data(conn: sqlite3.Connection):
    """Return (list of tx feature dicts, list of (category, subcategory, property_code))."""
    cur = conn.execute("""
        SELECT c.tx_id, c.match_text, c.amount, c.effective_subcategory, c.source_bank
        FROM transactions_canonical c
        INNER JOIN (
            SELECT tx_id, MAX(label_version) AS mv FROM transactions_labels GROUP BY tx_id
        ) l ON c.tx_id = l.tx_id
        JOIN transactions_labels lab ON lab.tx_id = c.tx_id AND lab.label_version = l.mv
        WHERE c.is_superseded = 0
          AND lab.category IS NOT NULL AND lab.category != ''
          AND lab.subcategory IS NOT NULL AND lab.subcategory != ''
    """)
    rows = [dict(row) for row in cur.fetchall()]
    cur = conn.execute("""
        SELECT tx_id, category, subcategory, property_code
        FROM transactions_labels l1
        WHERE label_version = (SELECT MAX(label_version) FROM transactions_labels l2 WHERE l2.tx_id = l1.tx_id)
    """)
    labels_by_tx = {row["tx_id"]: (row["category"], row["subcategory"], row["property_code"] or "") for row in cur.fetchall()}

    X_dicts = []
    y_triples = []
    for r in rows:
        if r["tx_id"] not in labels_by_tx:
            continue
        cat, subcat, prop = labels_by_tx[r["tx_id"]]
        if not cat or not subcat:
            continue
        X_dicts.append({
            "match_text": (r["match_text"] or "").strip() or "(none)",
            "amount": float(r["amount"] or 0),
            "effective_subcategory": (r["effective_subcategory"] or "").strip() or "__none__",
            "source_bank": (r["source_bank"] or "").strip() or "__none__",
        })
        y_triples.append((cat, subcat, prop))

    return X_dicts, y_triples


def _encode_with_unknown(encoder, values):
    """Encode list of values; use -1 for unseen labels."""
    out = []
    classes = set(encoder.classes_)
    for v in values:
        if v in classes:
            out.append(encoder.transform([v])[0])
        else:
            out.append(-1)
    return np.array(out).reshape(-1, 1)


def _build_feature_matrix(X_dicts, vec_text, scaler_amount, enc_subcat, enc_bank, fit=False):
    """Build numeric feature matrix from list of feature dicts. If fit=True, fit transformers."""
    texts = [d["match_text"] for d in X_dicts]
    amounts = np.array([d["amount"] for d in X_dicts]).reshape(-1, 1)
    subcats = [d["effective_subcategory"] for d in X_dicts]
    banks = [d["source_bank"] for d in X_dicts]

    if fit:
        X_text = vec_text.fit_transform(texts)
        amounts_scaled = scaler_amount.fit_transform(amounts)
        enc_subcat.fit(subcats)
        enc_bank.fit(banks)
    else:
        X_text = vec_text.transform(texts)
        amounts_scaled = scaler_amount.transform(amounts)

    subcat_enc = _encode_with_unknown(enc_subcat, subcats)
    bank_enc = _encode_with_unknown(enc_bank, banks)

    from scipy.sparse import hstack
    return hstack([X_text, amounts_scaled, subcat_enc, bank_enc])


def train(db_path: Path | str | None = None, model_path: Path | str | None = None) -> dict:
    """Train ML model from DB labels and save to model_path. Returns stats."""
    db = db_path or DB_PATH
    path = model_path or MODEL_PATH
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with get_db(db) as conn:
        X_dicts, y_triples = _get_training_data(conn)
    if len(X_dicts) < 20:
        return {"ok": False, "reason": "need_at_least_20_labeled", "n": len(X_dicts)}

    vec_text = TfidfVectorizer(max_features=1500, min_df=1, strip_accents="unicode", lowercase=True)
    scaler_amount = StandardScaler()
    enc_subcat = LabelEncoder()
    enc_bank = LabelEncoder()

    y_cat = [y[0] for y in y_triples]
    y_sub = [y[1] for y in y_triples]
    y_prop = [y[2] for y in y_triples]

    X = _build_feature_matrix(X_dicts, vec_text, scaler_amount, enc_subcat, enc_bank, fit=True)

    clf_cat = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    clf_sub = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=43, n_jobs=-1)
    clf_prop = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=44, n_jobs=-1)

    clf_cat.fit(X, y_cat)
    clf_sub.fit(X, y_sub)
    clf_prop.fit(X, y_prop)

    payload = {
        "vec_text": vec_text,
        "scaler_amount": scaler_amount,
        "enc_subcat": enc_subcat,
        "enc_bank": enc_bank,
        "clf_category": clf_cat,
        "clf_subcategory": clf_sub,
        "clf_property": clf_prop,
    }
    joblib.dump(payload, path)
    return {"ok": True, "n": len(X_dicts), "path": str(path)}


def load_model(model_path: Path | str | None = None):
    """Load persisted model. Returns dict of artifacts or None if file missing."""
    path = model_path or MODEL_PATH
    path = Path(path)
    if not path.exists():
        return None
    return joblib.load(path)


def predict_one(tx: dict, model: dict) -> tuple[str | None, str | None, str | None, float]:
    """Predict (category, subcategory, property_code, confidence) for one transaction dict.
    tx should have match_text, amount, effective_subcategory, source_bank (or compatible keys).
    """
    d = {
        "match_text": (tx.get("match_text") or tx.get("memo") or "").strip() or "(none)",
        "amount": float(tx.get("amount") or 0),
        "effective_subcategory": (tx.get("effective_subcategory") or "").strip() or "__none__",
        "source_bank": (tx.get("source_bank") or "").strip() or "__none__",
    }
    X = _build_feature_matrix(
        [d],
        model["vec_text"],
        model["scaler_amount"],
        model["enc_subcat"],
        model["enc_bank"],
        fit=False,
    )

    p_cat = model["clf_category"].predict_proba(X)[0]
    p_sub = model["clf_subcategory"].predict_proba(X)[0]
    p_prop = model["clf_property"].predict_proba(X)[0]

    cat_classes = model["clf_category"].classes_
    sub_classes = model["clf_subcategory"].classes_
    prop_classes = model["clf_property"].classes_

    max_cat = p_cat.max()
    max_sub = p_sub.max()
    max_prop = p_prop.max()
    confidence = (max_cat * max_sub * max_prop) ** (1 / 3)

    cat = cat_classes[p_cat.argmax()]
    sub = sub_classes[p_sub.argmax()]
    prop = prop_classes[p_prop.argmax()]

    return (cat, sub, prop, float(confidence))
