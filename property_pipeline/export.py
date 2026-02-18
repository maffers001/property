"""Export functions to produce XLSX/CSV files compatible with 3.0 MonthlySummary."""

from pathlib import Path

import pandas as pd


def build_output_dataframe(transactions: list[dict], labels: list[dict]) -> pd.DataFrame:
    """Join canonical transactions with labels into the output schema.

    Output columns (matching 3.0 MonthlySummary expectations):
        Date (index), Account, Amount, Subcategory, Memo, Property, Description, Cat, Subcat
    """
    tx_df = pd.DataFrame(transactions)
    lab_df = pd.DataFrame(labels)

    tx_df = tx_df[tx_df["is_superseded"] == 0].copy()

    merged = tx_df.merge(lab_df, on="tx_id", how="left")

    merged["Date"] = pd.to_datetime(merged["posted_date"], format="%Y-%m-%d")
    merged["Account"] = merged["source_account"]
    merged["Amount"] = merged["amount"]
    merged["Subcategory"] = merged["effective_subcategory"]
    merged["Memo"] = merged["memo"]
    merged["Property"] = merged["property_code"].fillna("")
    desc_y = merged.get("description_y")
    desc_x = merged.get("description_x")
    if desc_y is not None:
        merged["Description"] = desc_y.fillna("").astype(str)
    elif desc_x is not None:
        merged["Description"] = desc_x.fillna("").astype(str)
    else:
        merged["Description"] = ""
    merged["Cat"] = merged["category"].fillna("")
    merged["Subcat"] = merged["subcategory"].fillna("")

    merged.set_index("Date", inplace=True)
    merged.sort_index(inplace=True)

    output_cols = ["Account", "Amount", "Subcategory", "Memo", "Property", "Description", "Cat", "Subcat"]
    result = merged[output_cols].copy()

    return result


def write_xlsx(df: pd.DataFrame, output_path: Path) -> None:
    """Write the dataframe to XLSX."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, engine="openpyxl")


def write_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Write the dataframe to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)


def write_review_queue(
    transactions: list[dict],
    labels: list[dict],
    output_path: Path,
) -> int:
    """Write review queue XLSX with only needs_review=1 rows.

    Returns the count of review items.
    """
    tx_df = pd.DataFrame(transactions)
    lab_df = pd.DataFrame(labels)
    tx_df = tx_df[tx_df["is_superseded"] == 0].copy()

    merged = tx_df.merge(lab_df, on="tx_id", how="left")
    review = merged[merged["needs_review"] == 1].copy()

    if review.empty:
        return 0

    review["Date"] = pd.to_datetime(review["posted_date"])
    review.set_index("Date", inplace=True)
    review.sort_index(inplace=True)

    cols = [
        "tx_id", "source_bank", "source_account", "amount",
        "counterparty", "reference", "memo", "type",
        "effective_subcategory",
        "property_code", "category", "subcategory",
        "confidence", "rule_id", "rule_strength",
    ]
    existing = [c for c in cols if c in review.columns]
    out = review[existing]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(output_path, engine="openpyxl")

    return len(out)


def write_diagnostic_ddcheck(
    transactions: list[dict],
    labels: list[dict],
    output_path: Path,
) -> None:
    """Write DDCheck equivalent: all direct debits and Beals for mortgage/property checking."""
    import re

    tx_df = pd.DataFrame(transactions)
    lab_df = pd.DataFrame(labels)
    tx_df = tx_df[tx_df["is_superseded"] == 0].copy()
    merged = tx_df.merge(lab_df, on="tx_id", how="left")

    mask_dd = merged["effective_subcategory"].fillna("").str.contains(
        r"DIRECT[ ]?DEBIT|Direct Debit", case=False, regex=True
    )
    mask_beals = merged["memo"].fillna("").str.match(r"^BEALS.*$", case=False)
    dd = merged[mask_dd | mask_beals].copy()

    dd["Date"] = pd.to_datetime(dd["posted_date"])
    dd.set_index("Date", inplace=True)
    dd.sort_index(inplace=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dd.to_csv(output_path)


def write_diagnostic_catcheck(
    transactions: list[dict],
    labels: list[dict],
    output_path: Path,
) -> None:
    """Write CatCheck equivalent: all categorised transactions."""
    tx_df = pd.DataFrame(transactions)
    lab_df = pd.DataFrame(labels)
    tx_df = tx_df[tx_df["is_superseded"] == 0].copy()
    merged = tx_df.merge(lab_df, on="tx_id", how="left")

    merged["Date"] = pd.to_datetime(merged["posted_date"])
    merged.set_index("Date", inplace=True)
    merged.sort_index(inplace=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path)
