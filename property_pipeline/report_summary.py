"""Report aggregations matching 3.0 MonthlySummary notebook. Used by the API to return JSON."""
import datetime
import os
from pathlib import Path

import pandas as pd
from dateutil.rrule import rrule, MONTHLY

from .config import CHECKED_DIR


def _month_str_to_range(month_str: str) -> tuple[str, str]:
    """OCT2025 -> ('2025-10-01', '2025-10-31')."""
    dt = pd.to_datetime("01" + month_str, format="%d%b%Y")
    start = dt.strftime("%Y-%m-%d")
    # last day of month
    next_month = dt + pd.offsets.MonthBegin(1)
    end_dt = next_month - pd.Timedelta(days=1)
    end = end_dt.strftime("%Y-%m-%d")
    return start, end


def load_data(start: str, end: str, checked_dir: Path | None = None) -> pd.DataFrame:
    """Load checked files for date range. start/end as YYYY-MM-DD.
    Returns DataFrame with DatetimeIndex and columns Account, Amount, Subcategory, Memo, Property, Description, Cat, Subcat.
    """
    checked_dir = checked_dir or CHECKED_DIR
    start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
    dates = list(rrule(MONTHLY, dtstart=start_date, until=end_date))

    df_all = pd.DataFrame(columns=["Account", "Amount", "Subcategory", "Memo", "Property", "Description", "Cat", "Subcat"])

    for date in dates:
        date_str = date.strftime("%b").upper() + date.strftime("%Y")
        base = checked_dir / f"{date_str}_codedAndCategorised"
        xls_path = base.with_suffix(".xlsx")
        csv_path = base.with_suffix(".csv")
        if xls_path.exists():
            df_temp = pd.read_excel(xls_path, index_col=0, engine="openpyxl")
        elif csv_path.exists():
            df_temp = pd.read_csv(csv_path, index_col=0, parse_dates=True, dayfirst=True)
        else:
            continue
        df_temp.index = pd.to_datetime(df_temp.index, dayfirst=True, errors="coerce")
        df_temp = df_temp.dropna(how="all", subset=df_temp.columns)
        needed = ["Account", "Amount", "Subcategory", "Memo", "Property", "Description", "Cat", "Subcat"]
        for c in needed:
            if c not in df_temp.columns:
                df_temp[c] = ""
        df_all = pd.concat([df_all, df_temp[needed]])
    if df_all.empty:
        return df_all
    return df_all[["Account", "Amount", "Subcategory", "Memo", "Property", "Description", "Cat", "Subcat"]]


def sum_of(df: pd.DataFrame, cat: str) -> pd.Series:
    g = pd.Grouper(freq="ME")
    return df.loc[df["Cat"] == cat, "Amount"].groupby(g).sum()


def sum_of_subcat(df: pd.DataFrame, subcat: str) -> pd.Series:
    g = pd.Grouper(freq="ME")
    return df.loc[df["Subcat"] == subcat, "Amount"].groupby(g).sum()


def get_pty_summary(df: pd.DataFrame) -> pd.DataFrame:
    df_pty = pd.DataFrame()
    df_pty["Mortgage"] = sum_of(df, "Mortgage")
    df_pty["PropertyExpense"] = sum_of(df, "PropertyExpense")
    df_pty["ServiceCharge"] = sum_of(df, "ServiceCharge")
    df_pty["OurRent"] = sum_of(df, "OurRent")
    df_pty["BealsRent"] = sum_of(df, "BealsRent")
    df_pty = df_pty.fillna(0)
    df_pty["TotalRent"] = df_pty["OurRent"] + df_pty["BealsRent"]
    df_pty["NetProfit"] = (
        df_pty["OurRent"] + df_pty["BealsRent"] + df_pty["Mortgage"]
        + df_pty["PropertyExpense"] + df_pty["ServiceCharge"]
    )
    return df_pty


def get_outgoings(df: pd.DataFrame) -> pd.DataFrame:
    df_out = pd.DataFrame()
    df_out["MTPersonal"] = sum_of(df.loc[df["Account"] == "20-74-09 60458872"], "PersonalExpense")
    df_out["MTCar"] = (
        sum_of_subcat(df, "MTCar").fillna(0).add(sum_of(df, "Car").fillna(0), fill_value=0)
    )
    df_out["IVPersonal"] = sum_of(df.loc[~(df["Account"] == "20-74-09 60458872")], "PersonalExpense")
    df_out["IVCar"] = sum_of_subcat(df, "IVCar")
    df_out["SFLoan"] = sum_of_subcat(df, "SFLoan")
    df_out["Hilltop"] = sum_of(df, "Hilltop")
    df_out["RegularPayment"] = sum_of(
        df.loc[~df["Subcat"].isin(["MTCar", "IVCar", "SFLoan"])], "RegularPayment"
    )
    df_out["SchoolFee"] = sum_of(df, "SchoolFee")
    df_out["HMRCDD"] = sum_of(df, "HMRCDD")
    df_out["HMRCPayment"] = sum_of(df, "HMRCPayment")
    df_out["OtherIncome"] = sum_of(df, "OtherIncome")
    df_out["OtherExpense"] = sum_of(df, "OtherExpense")
    df_out = df_out.fillna(0)
    df_out["HMRC"] = df_out["HMRCDD"] + df_out["HMRCPayment"]
    df_out["TotalOther"] = df_out["OtherIncome"] + df_out["OtherExpense"]
    df_out["TotalOutgoings"] = (
        df_out["IVPersonal"] + df_out["IVCar"] + df_out["SchoolFee"]
        + df_out["Hilltop"] + df_out["RegularPayment"]
        + df_out["HMRCDD"] + df_out["HMRCPayment"] + df_out["TotalOther"]
    )
    df_out["TotalOutgoingsExclSchool"] = (
        df_out["IVPersonal"] + df_out["IVCar"] + df_out["Hilltop"]
        + df_out["RegularPayment"] + df_out["HMRCDD"] + df_out["HMRCPayment"] + df_out["TotalOther"]
    )
    return df_out


def get_personal_spending_summary(df: pd.DataFrame) -> pd.DataFrame:
    df_ps = pd.DataFrame()
    df_ps["TotalPersonalExpense"] = sum_of(df, "PersonalExpense")
    df_ps["Garage"] = sum_of_subcat(df, "Garage")
    food_cols = [
        "Tesco", "Garage", "M&S", "Waitrose", "Morrisons", "LIDL",
        "COOP", "Budgens", "Costco", "A1 Foods", "Sainsburys", "ASDA",
    ]
    food_parts = [sum_of_subcat(df, x) for x in food_cols]
    df_ps["Food"] = pd.concat(food_parts, axis=1).sum(axis=1)
    df_ps["Body"] = sum_of_subcat(df, "Pharmacy/Opticians/Dental")
    df_ps["Beauty"] = sum_of_subcat(df, "Beauty")
    df_ps["EatingOut"] = sum_of_subcat(df, "EatingOut")
    df_ps["Coffee"] = sum_of_subcat(df, "Coffee")
    df_ps["Car"] = sum_of_subcat(df, "Car")
    df_ps["Amazon"] = sum_of_subcat(df, "Amazon")
    df_ps["Clothing"] = sum_of_subcat(df, "Clothing")
    df_ps["Household"] = sum_of_subcat(df, "Household")
    df_ps["Holiday"] = sum_of_subcat(df, "Holiday")
    df_ps["Cash"] = sum_of_subcat(df, "Cash")
    df_ps["Other"] = sum_of_subcat(df, "Other")
    df_ps = df_ps.fillna(0)
    return df_ps


def _dataframe_to_monthly_list(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame with DatetimeIndex (month-end) to list of { month: 'OCT2025', ... col values }."""
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return []
    out = []
    for ts in df.index:
        month_str = ts.strftime("%b").upper() + ts.strftime("%Y")
        row = {"month": month_str}
        for c in df.columns:
            v = df.loc[ts, c]
            row[c] = float(v) if pd.notna(v) else 0.0
        out.append(row)
    return out


def build_report_summary(month_from: str, month_to: str, checked_dir: Path | None = None) -> dict:
    """Build property summary, outgoings, personal spending for the given month range (e.g. OCT2025, NOV2025)."""
    start, end = _month_str_to_range(month_from)
    _, end_last = _month_str_to_range(month_to)
    end = end_last
    df = load_data(start, end, checked_dir=checked_dir)
    if df.empty:
        return {
            "property_summary": [],
            "outgoings": [],
            "personal_spending": [],
        }
    pty = get_pty_summary(df)
    out = get_outgoings(df)
    ps = get_personal_spending_summary(df)
    return {
        "property_summary": _dataframe_to_monthly_list(pty),
        "outgoings": _dataframe_to_monthly_list(out),
        "personal_spending": _dataframe_to_monthly_list(ps),
    }
