"""Backtesting framework: compare pipeline output against XLSX ground truth."""

from pathlib import Path

import pandas as pd
import numpy as np

from .config import BANK_DOWNLOAD_DIR, CHECKED_DIR
from .importers import load_month_files
from .engine import run_engine
from .rules_seed import get_all_rules, PROPERTIES_SEED
from .export import build_output_dataframe


CRITICAL_CATEGORIES = {"Mortgage", "OurRent", "BealsRent", "PropertyExpense", "ServiceCharge"}
PROPERTY_REQUIRED_CATEGORIES = {"Mortgage", "OurRent", "BealsRent", "PropertyExpense"}


def load_ground_truth(month_str: str, checked_dir: Path | None = None) -> pd.DataFrame | None:
    """Load the manually-checked XLSX ground truth for a month."""
    cd = checked_dir or CHECKED_DIR
    xlsx_path = cd / f"{month_str}_codedAndCategorised.xlsx"
    csv_path = cd / f"{month_str}_codedAndCategorised.csv"

    if xlsx_path.exists():
        df = pd.read_excel(xlsx_path, engine="openpyxl", index_col=0, parse_dates=True)
    elif csv_path.exists():
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True, dayfirst=True)
    else:
        return None

    for col in ["Property", "Cat", "Subcat", "Description"]:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    return df


def run_backtest_month(
    month_str: str,
    bank_download_dir: Path | None = None,
    checked_dir: Path | None = None,
) -> dict | None:
    """Run the pipeline on a month and compare against ground truth.

    Returns a metrics dict or None if ground truth is missing.
    """
    bd_dir = bank_download_dir or BANK_DOWNLOAD_DIR

    truth = load_ground_truth(month_str, checked_dir)
    if truth is None:
        return None

    try:
        _, canonical_rows = load_month_files(bd_dir, month_str)
    except Exception as e:
        print(f"  Cannot load bank files for {month_str}: {e}")
        return None

    if not canonical_rows:
        return None

    rules = get_all_rules()
    properties_set = {p["property_code"] for p in PROPERTIES_SEED}
    labels = run_engine(canonical_rows, rules, properties_set)

    predicted = build_output_dataframe(canonical_rows, labels)

    return compare(predicted, truth, month_str)


def compare(predicted: pd.DataFrame, truth: pd.DataFrame, month_str: str = "") -> dict:
    """Compare predicted output against ground truth.

    Both DataFrames should have Date as index and columns:
    Account, Amount, Subcategory, Memo, Property, Description, Cat, Subcat
    """
    truth = truth.copy()
    predicted = predicted.copy()

    for col in ["Property", "Cat", "Subcat"]:
        truth[col] = truth[col].astype(str).str.strip()
        predicted[col] = predicted[col].astype(str).str.strip()
        truth.loc[truth[col].isin(["nan", "None", ""]), col] = ""
        predicted.loc[predicted[col].isin(["nan", "None", ""]), col] = ""

    truth["Amount"] = pd.to_numeric(truth["Amount"], errors="coerce").fillna(0)
    predicted["Amount"] = pd.to_numeric(predicted["Amount"], errors="coerce").fillna(0)

    truth["_date_str"] = truth.index.strftime("%Y-%m-%d") if hasattr(truth.index, "strftime") else truth.index.astype(str)
    predicted["_date_str"] = predicted.index.strftime("%Y-%m-%d") if hasattr(predicted.index, "strftime") else predicted.index.astype(str)

    truth["Account"] = truth["Account"].astype(str).str.strip()
    predicted["Account"] = predicted["Account"].astype(str).str.strip()
    truth["Memo"] = truth["Memo"].astype(str).str.strip()
    predicted["Memo"] = predicted["Memo"].astype(str).str.strip()

    # Build join key
    truth["_key"] = truth["_date_str"] + "|" + truth["Account"] + "|" + truth["Amount"].round(2).astype(str) + "|" + truth["Memo"]
    predicted["_key"] = predicted["_date_str"] + "|" + predicted["Account"] + "|" + predicted["Amount"].round(2).astype(str) + "|" + predicted["Memo"]

    # Match rows
    truth_keys = truth["_key"].tolist()
    pred_keys = predicted["_key"].tolist()

    matched_truth = []
    matched_pred = []
    used_pred = set()

    for t_idx, t_key in enumerate(truth_keys):
        for p_idx, p_key in enumerate(pred_keys):
            if p_idx not in used_pred and t_key == p_key:
                matched_truth.append(t_idx)
                matched_pred.append(p_idx)
                used_pred.add(p_idx)
                break

    n_truth = len(truth)
    n_matched = len(matched_truth)
    row_match_rate = n_matched / n_truth if n_truth > 0 else 0

    # Per-column accuracy
    cat_correct = 0
    cat_critical_correct = 0
    cat_critical_total = 0
    prop_correct = 0
    prop_total = 0
    subcat_correct = 0
    full_correct = 0
    mismatched_amount = 0.0

    cat_confusion = {}

    for i in range(n_matched):
        t_row = truth.iloc[matched_truth[i]]
        p_row = predicted.iloc[matched_pred[i]]

        t_cat = t_row["Cat"]
        p_cat = p_row["Cat"]
        t_prop = t_row["Property"]
        p_prop = p_row["Property"]
        t_sub = t_row["Subcat"]
        p_sub = p_row["Subcat"]

        # Category
        cat_match = (t_cat == p_cat)
        if cat_match:
            cat_correct += 1
        else:
            mismatched_amount += abs(t_row["Amount"])

        # Confusion matrix
        key = (t_cat, p_cat)
        cat_confusion[key] = cat_confusion.get(key, 0) + 1

        # Critical categories
        if t_cat in CRITICAL_CATEGORIES:
            cat_critical_total += 1
            if cat_match:
                cat_critical_correct += 1

        # Property
        if t_cat in PROPERTY_REQUIRED_CATEGORIES:
            prop_total += 1
            if t_prop == p_prop:
                prop_correct += 1

        # Subcategory
        if t_sub == p_sub:
            subcat_correct += 1

        # Full label
        if cat_match and t_prop == p_prop and t_sub == p_sub:
            full_correct += 1

    metrics = {
        "month": month_str,
        "truth_rows": n_truth,
        "predicted_rows": len(predicted),
        "matched_rows": n_matched,
        "row_match_rate": round(row_match_rate, 4),
        "category_accuracy": round(cat_correct / n_matched, 4) if n_matched else 0,
        "critical_category_accuracy": round(cat_critical_correct / cat_critical_total, 4) if cat_critical_total else 0,
        "property_accuracy": round(prop_correct / prop_total, 4) if prop_total else 0,
        "subcategory_accuracy": round(subcat_correct / n_matched, 4) if n_matched else 0,
        "full_label_accuracy": round(full_correct / n_matched, 4) if n_matched else 0,
        "financial_impact_mismatched": round(mismatched_amount, 2),
        "confusion_matrix": cat_confusion,
    }

    return metrics


def run_backtest_all(
    bank_download_dir: Path | None = None,
    checked_dir: Path | None = None,
    months: list[str] | None = None,
) -> list[dict]:
    """Run backtest over all available months with ground truth.

    If months is None, discovers months from checked/ folder.
    """
    cd = checked_dir or CHECKED_DIR
    bd = bank_download_dir or BANK_DOWNLOAD_DIR

    if months is None:
        months = []
        for f in sorted(cd.glob("*_codedAndCategorised.xlsx")):
            m = f.name.replace("_codedAndCategorised.xlsx", "")
            months.append(m)

    results = []
    for m in months:
        print(f"Backtesting {m}...")
        r = run_backtest_month(m, bd, cd)
        if r:
            results.append(r)
            print(f"  Cat={r['category_accuracy']:.1%}  CritCat={r['critical_category_accuracy']:.1%}  "
                  f"Prop={r['property_accuracy']:.1%}  Full={r['full_label_accuracy']:.1%}  "
                  f"Matched={r['row_match_rate']:.1%}")
        else:
            print(f"  Skipped (no ground truth or bank files)")

    if results:
        avg_cat = np.mean([r["category_accuracy"] for r in results])
        avg_crit = np.mean([r["critical_category_accuracy"] for r in results if r["critical_category_accuracy"] > 0])
        avg_prop = np.mean([r["property_accuracy"] for r in results if r["property_accuracy"] > 0])
        avg_full = np.mean([r["full_label_accuracy"] for r in results])
        print(f"\nOverall averages across {len(results)} months:")
        print(f"  Category: {avg_cat:.1%}")
        print(f"  Critical Category: {avg_crit:.1%}")
        print(f"  Property: {avg_prop:.1%}")
        print(f"  Full Label: {avg_full:.1%}")

    return results
