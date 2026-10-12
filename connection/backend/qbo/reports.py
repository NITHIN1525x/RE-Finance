"""Summaries of QuickBooks responses for the /test endpoint. Only figures QuickBooks returned are
reported; a missing section is omitted rather than shown as 0."""
from datetime import date
from decimal import Decimal, InvalidOperation

# Top-level P&L sections, keyed by the `group` attribute QuickBooks puts on each section row.
PNL_GROUPS = {
    "Income": "total_income",
    "COGS": "cost_of_goods_sold",
    "GrossProfit": "gross_profit",
    "Expenses": "total_expenses",
    "NetOperatingIncome": "net_operating_income",
    "OtherIncome": "other_income",
    "OtherExpenses": "other_expenses",
    "NetOtherIncome": "net_other_income",
    "NetIncome": "net_income",
}


def last_12_months(today=None):
    """First day of the month 11 months ago through today (12 calendar months, current one partial)."""
    today = today or date.today()
    month_index = today.year * 12 + (today.month - 1) - 11
    return date(month_index // 12, month_index % 12 + 1, 1), today


def _amount(value):
    try:
        return str(Decimal(value).quantize(Decimal("0.01")))
    except (InvalidOperation, TypeError, ValueError):
        return None


def summarize_company(payload):
    info = payload.get("CompanyInfo", {})
    return {"name": info.get("CompanyName"), "legal_name": info.get("LegalName"), "country": info.get("Country")}


def summarize_pnl(payload):
    header = payload.get("Header", {})
    totals = {}
    for row in payload.get("Rows", {}).get("Row", []):
        key = PNL_GROUPS.get(row.get("group"))
        cols = row.get("Summary", {}).get("ColData", [])
        if key and len(cols) >= 2:
            amount = _amount(cols[-1].get("value"))
            if amount is not None:
                totals[key] = amount
    return {
        "start_date": header.get("StartPeriod"),
        "end_date": header.get("EndPeriod"),
        "currency": header.get("Currency"),
        "basis": header.get("ReportBasis"),
        "totals": totals,
        "has_data": bool(totals),
    }
