"""Reports API: summary aggregations from checked data."""
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from property_pipeline.report_summary import build_report_summary
from property_pipeline.config import CHECKED_DIR

from backend.auth import get_current_user

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/summary")
def get_reports_summary(
    month: str | None = Query(None, description="Single month e.g. OCT2025"),
    from_month: str | None = Query(None, alias="from", description="Start month e.g. OCT2025"),
    to: str | None = Query(None, description="End month e.g. NOV2025"),
    user: dict = Depends(get_current_user),
):
    """Return property summary, outgoings, personal spending for the given month or range."""
    if month:
        month_from = month_to = month
    elif from_month and to:
        month_from = from_month
        month_to = to
    else:
        month_from = month_to = None
    if not month_from or not month_to:
        return {
            "property_summary": [],
            "outgoings": [],
            "personal_spending": [],
        }
    result = build_report_summary(month_from, month_to, checked_dir=CHECKED_DIR)
    return result
