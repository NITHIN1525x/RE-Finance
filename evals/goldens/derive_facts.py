"""Derive golden FACTS straight from the raw workbook cells. Independent of the skill's extractor.

Uses plain openpyxl (cached values), finds rows by their own labels, and records for every fact:
the value, the sheet, the exact cells, and the formula used, so a human can audit each golden in Excel.

Run:  .claude/skills/monthly-trend-analysis/.venv/Scripts/python evals/goldens/derive_facts.py
      -> writes evals/goldens/source_facts.json   (add --check to verify the committed file instead)
"""
import json
import statistics
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter as L

REPO = Path(__file__).resolve().parents[2]
ABC = next((REPO / "data").glob("ABC Inc*.xlsx"))
BLUEBIRD = REPO / ".claude/skills/monthly-trend-analysis/tests/test_data/bluebird-bakery.xlsx"
OUT = Path(__file__).resolve().parent / "source_facts.json"

facts = {}


def fact(fid, value, sheet, cells, formula, note=None):
    facts[fid] = {"value": value, "sheet": sheet, "cells": cells, "formula": formula, **({"note": note} if note else {})}


def row_of(ws, label, cols=(1, 2, 3)):
    hits = [r for r in range(1, ws.max_row + 1) for c in cols if ws.cell(r, c).value == label]
    if len(hits) != 1:
        raise ValueError(f"label {label!r} found {len(hits)} times in {ws.title}")
    return hits[0]


def v(ws, r, c):
    x = ws.cell(r, c).value
    return 0.0 if x is None else float(x)


def pct(a, b):
    return (a - b) / abs(b) * 100


# --------------------------------------------------------------------------------------------- ABC Inc
wb = openpyxl.load_workbook(ABC, data_only=True)
IS, BS = wb["Income Statement"], wb["Balance Sheet"]
assert IS.cell(5, 3).value == "Jun 2026" and IS.cell(5, 4).value == "May 2026" and IS.cell(5, 15).value == "Jun 2025"
assert IS.cell(5, 9).value == "Dec 2025" and IS.cell(5, 14).value == "Jul 2025"
JUN, MAY, JUN25, DEC25 = 3, 4, 15, 9          # IS columns C, D, O, I (sheet is newest-first)
S = "Income Statement"

r_inc, r_cogs, r_gp, r_opex, r_ni = (row_of(IS, x) for x in
                                     ("Total Income", "Total Cost of Goods Sold", "Gross Profit", "Total Operating Expenses", "Net Income"))
inc = lambda c: v(IS, r_inc, c)
fact("abc.revenue.jun2026", inc(JUN), S, [f"C{r_inc}"], "Total Income, Jun 2026")
fact("abc.revenue.may2026", inc(MAY), S, [f"D{r_inc}"], "Total Income, May 2026")
fact("abc.revenue.mom_pct", pct(inc(JUN), inc(MAY)), S, [f"C{r_inc}", f"D{r_inc}"], f"(C{r_inc}-D{r_inc})/D{r_inc}*100")
fact("abc.revenue.jun2025", inc(JUN25), S, [f"O{r_inc}"], "Total Income, Jun 2025")
fact("abc.revenue.yoy_pct", pct(inc(JUN), inc(JUN25)), S, [f"C{r_inc}", f"O{r_inc}"], f"(C{r_inc}-O{r_inc})/O{r_inc}*100")
avg6 = statistics.mean(inc(c) for c in range(MAY, MAY + 6))
fact("abc.revenue.prior6_avg", avg6, S, [f"D{r_inc}:I{r_inc}"], f"AVERAGE(D{r_inc}:I{r_inc}) (Dec 2025..May 2026)")
fact("abc.revenue.vs_prior6_pct", pct(inc(JUN), avg6), S, [f"C{r_inc}", f"D{r_inc}:I{r_inc}"], "(Jun - prior-6 average)/average*100")
fact("abc.revenue.may_is_max", inc(MAY) == max(inc(c) for c in range(MAY, 21)), S, [f"D{r_inc}:T{r_inc}"],
     "May 2026 is the maximum of all months before Jun 2026")
ttm = sum(inc(c) for c in range(JUN, JUN + 12))
fact("abc.revenue.ttm", ttm, S, [f"C{r_inc}:N{r_inc}"], f"SUM(C{r_inc}:N{r_inc}) (Jul 2025..Jun 2026)")
r_uf = row_of(IS, "Usage Fees")
fact("abc.usage_fees.jun2026", v(IS, r_uf, JUN), S, [f"C{r_uf}"], "Usage Fees, Jun 2026")
fact("abc.usage_fees.mom_pct", pct(v(IS, r_uf, JUN), v(IS, r_uf, MAY)), S, [f"C{r_uf}", f"D{r_uf}"], f"(C{r_uf}-D{r_uf})/D{r_uf}*100")
fact("abc.usage_fees.ttm_share_pct", sum(v(IS, r_uf, c) for c in range(JUN, JUN + 12)) / ttm * 100, S,
     [f"C{r_uf}:N{r_uf}", f"C{r_inc}:N{r_inc}"], "SUM(Usage Fees TTM)/SUM(Total Income TTM)*100")
n_streams = row_of(IS, "Total Income") - row_of(IS, "Income", cols=(1,)) - 1
fact("abc.revenue.stream_count", n_streams, S, [f"B{row_of(IS, 'Income', cols=(1,)) + 1}:B{r_inc - 1}"], "rows between 'Income' header and 'Total Income'")

gp = lambda c: v(IS, r_gp, c)
fact("abc.gm_pct.jun2026", gp(JUN) / inc(JUN) * 100, S, [f"C{r_gp}", f"C{r_inc}"], f"C{r_gp}/C{r_inc}*100")
fact("abc.gm_pct.may2026", gp(MAY) / inc(MAY) * 100, S, [f"D{r_gp}", f"D{r_inc}"], f"D{r_gp}/D{r_inc}*100")
fact("abc.gm_pct.jun2025", gp(JUN25) / inc(JUN25) * 100, S, [f"O{r_gp}", f"O{r_inc}"], f"O{r_gp}/O{r_inc}*100")
fact("abc.gm_pct.ttm", sum(gp(c) for c in range(JUN, JUN + 12)) / ttm * 100, S, [f"C{r_gp}:N{r_gp}", f"C{r_inc}:N{r_inc}"],
     "SUM(GP TTM)/SUM(Revenue TTM)*100")
fact("abc.cogs.jun2026", v(IS, r_cogs, JUN), S, [f"C{r_cogs}"], "Total Cost of Goods Sold, Jun 2026")
fact("abc.gross_profit.jun2026", gp(JUN), S, [f"C{r_gp}"], "Gross Profit, Jun 2026")
fact("abc.opex_total.jun2026", v(IS, r_opex, JUN), S, [f"C{r_opex}"], "Total Operating Expenses, Jun 2026")
ni = lambda c: v(IS, r_ni, c)
fact("abc.net_income.jun2026", ni(JUN), S, [f"C{r_ni}"], "Net Income, Jun 2026")
fact("abc.net_income.ttm", sum(ni(c) for c in range(JUN, JUN + 12)), S, [f"C{r_ni}:N{r_ni}"], f"SUM(C{r_ni}:N{r_ni})")
streak = 0
for c in range(JUN, 21):
    if ni(c) < 0:
        streak += 1
    else:
        break
fact("abc.net_income.negative_streak", streak, S, [f"C{r_ni}:{L(JUN + streak)}{r_ni}"], "consecutive negative months ending Jun 2026")
fact("abc.net_income.negative_months", sum(1 for c in range(3, 21) if ni(c) < 0), S, [f"C{r_ni}:T{r_ni}"], "COUNTIF(<0)")
fact("abc.net_income.dec2025", ni(DEC25), S, [f"I{r_ni}"], "Net Income, Dec 2025 (the only positive month)")

for fid, label in (("sbc", "Stock-Based Compensation Expense"), ("bonus", "Bonus"), ("income_tax_benefit", "Income Tax Benefit")):
    r = row_of(IS, label)
    others = [abs(v(IS, r, c)) for c in range(3, 21) if c != DEC25]
    fact(f"abc.{fid}.dec2025", v(IS, r, DEC25), S, [f"I{r}"], f"{label}, Dec 2025")
    fact(f"abc.{fid}.median_other_months", statistics.median(others), S, [f"C{r}:T{r} excl. I{r}"], f"median |{label}| over the other 17 months")

for fid, label in (("advisory_services", "Advisory Services"), ("federal_state_taxes", "Federal & State Taxes"),
                   ("mkt_misc", "Marketing/Advertising: Miscellaneous"), ("professional_fees", "Professional Fees")):
    r = row_of(IS, label)
    fact(f"abc.vanished.{fid}.jun2026", v(IS, r, JUN), S, [f"C{r}"], f"{label}, Jun 2026")
    fact(f"abc.vanished.{fid}.prior6_avg", statistics.mean(v(IS, r, c) for c in range(MAY, MAY + 6)), S, [f"D{r}:I{r}"],
         f"AVERAGE(D{r}:I{r}) {label}, Dec 2025..May 2026")

assert BS.cell(5, 4).value == "30 Jun 2026" and BS.cell(5, 10).value == "31 Dec 2025"
r_cash = row_of(BS, "Total Cash and Cash Equivalents")
fact("abc.cash.jun2026", v(BS, r_cash, 4), "Balance Sheet", [f"D{r_cash}"], "Total Cash and Cash Equivalents, 30 Jun 2026")
fact("abc.cash.may2026", v(BS, r_cash, 5), "Balance Sheet", [f"E{r_cash}"], "Total Cash and Cash Equivalents, 31 May 2026")
fact("abc.cash.dec2025", v(BS, r_cash, 10), "Balance Sheet", [f"J{r_cash}"], "Total Cash and Cash Equivalents, 31 Dec 2025")

# --------------------------------------------------------------------------------------------- Bluebird (portability)
wb = openpyxl.load_workbook(BLUEBIRD, data_only=True)
PL = wb["Profit and Loss"]
P = "Profit and Loss"
months = [PL.cell(4, c).value for c in range(2, 11)]
assert months[0].month == 1 and months[-1].month == 9 and PL.cell(4, 11).value == "Total"
fact("bb.months", len(months), P, ["B4:J4"], "month header cells (K4 is a 'Total' column, not a month)")
r_ps, r_bk, r_lg = row_of(PL, "Total for Professional Services"), row_of(PL, "Bookkeeping"), row_of(PL, "Legal")
MAR = 4                                                                     # column D = Mar 2026
stated, detail = v(PL, r_ps, MAR), v(PL, r_bk, MAR) + v(PL, r_lg, MAR)
fact("bb.prof_services.mar2026.stated", stated, P, [f"D{r_ps}"], "Total for Professional Services, Mar 2026")
fact("bb.prof_services.mar2026.detail_sum", detail, P, [f"D{r_bk}", f"D{r_lg}"], f"D{r_bk}+D{r_lg} (Bookkeeping + Legal)")
fact("bb.prof_services.mar2026.diff", stated - detail, P, [f"D{r_ps}", f"D{r_bk}", f"D{r_lg}"], "stated - detail sum")
other_ps_ok = all(abs(v(PL, r_ps, c) - v(PL, r_bk, c) - v(PL, r_lg, c)) < 0.01 for c in range(2, 11) if c != MAR)
fact("bb.prof_services.other_months_match", other_ps_ok, P, [f"B{r_ps}:J{r_ps}"], "stated = detail in every month except Mar")
r_cd = row_of(PL, "Charitable Donations")
fact("bb.charitable.all_blank", all(PL.cell(r_cd, c).value is None for c in range(2, 11)), P, [f"B{r_cd}:J{r_cd}"],
     "every month cell empty")
fact("bb.charitable.next_rows", [PL.cell(r_cd + k, 1).value for k in (1, 2)], P, [f"A{r_cd + 1}", f"A{r_cd + 2}"],
     "rows directly below the blank account (must not be grouped under it)")
r_ms = row_of(PL, "Mystery Shopper Program")
ms = [v(PL, r_ms, c) for c in range(2, 11)]
fact("bb.mystery_shopper.monthly", ms, P, [f"B{r_ms}:J{r_ms}"], "Jan..Sep 2026")
fact("bb.mystery_shopper.nonzero_before_sep", [m.strftime("%b %Y") for m, x in zip(months[:-1], ms[:-1]) if x],
     P, [f"B{r_ms}:I{r_ms}"], "months before Sep with a non-zero value (so it is NOT new in Sep)")
r_ws = row_of(PL, "Wholesale Accounts")
ws_vals = [PL.cell(r_ws, c).value for c in range(2, 11)]
fact("bb.wholesale.sep2026", float(ws_vals[-1]), P, [f"J{r_ws}"], "Wholesale Accounts, Sep 2026")
fact("bb.wholesale.blank_before_sep", all(x is None for x in ws_vals[:-1]), P, [f"B{r_ws}:I{r_ws}"], "empty Jan..Aug 2026")
r_ia = row_of(PL, "Instagram Ads")
fact("bb.instagram_ads.sep2026", v(PL, r_ia, 10), P, [f"J{r_ia}"], "Instagram Ads, Sep 2026")
r_exp = row_of(PL, "Total for Expenses")
fact("bb.expenses_total.monthly", [v(PL, r_exp, c) for c in range(2, 11)], P, [f"B{r_exp}:J{r_exp}"],
     "Total for Expenses, Jan..Sep 2026 (stated; equals the true detail sum in this workbook)")
fact("bb.charitable.zeros", [0.0] * len(months), P, [f"B{r_cd}:J{r_cd}"], "blank cells read as 0 in every month")
r_rev = row_of(PL, "Total for Revenue")
fact("bb.revenue.sep2026", v(PL, r_rev, 10), P, [f"J{r_rev}"], "Total for Revenue, Sep 2026")


def main():
    text = json.dumps(facts, indent=2, default=str)
    if "--check" in sys.argv:
        current = json.loads(OUT.read_text(encoding="utf-8"))
        same = json.loads(text) == current
        print("source_facts.json matches the workbooks" if same else "source_facts.json DIFFERS from the workbooks")
        sys.exit(0 if same else 1)
    OUT.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {len(facts)} facts to {OUT}")


if __name__ == "__main__":
    main()
