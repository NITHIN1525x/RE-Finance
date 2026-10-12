"""Render the analysis dict as a Markdown report a human reviewer can finish.

Every number in the report comes from the analysis dict. The narrative slot (NARRATIVE_MARKER) is left
for Claude/the reviewer to fill, using only figures already present in the report.
"""
from __future__ import annotations

NARRATIVE_MARKER = "<!-- NARRATIVE: replace this line with 4-8 bullets written from the flags below -->"


def money(v):
    if v is None:
        return "n/a"
    return f"({abs(v):,.0f})" if v < 0 else f"{v:,.0f}"


def pct(v, signed=True):
    if v is None:
        return "n/a"
    return f"{v:+.1f}%" if signed else f"{v:.1f}%"


def mom_cell(block):
    if block["mom_pct"] is not None:
        return pct(block["mom_pct"])
    if block["prior"] in (0, 0.0, None) and block["latest"]:
        return "from 0"   # prior month was zero; NOT necessarily a new line (that is a separate rule/flag)
    return "n/a"


def _row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table(header, rows, align=None):
    align = align or ["---"] + ["---:"] * (len(header) - 1)
    return "\n".join([_row(header), _row(align)] + [_row(r) for r in rows])


def _mom_series(values):
    out = [None]
    for prev, cur in zip(values, values[1:]):
        out.append(None if not prev else (cur - prev) / abs(prev) * 100)
    return out


def render(a, show_months=6):
    meta = a["meta"]
    labels = meta["month_labels"]
    k = min(show_months, len(labels))
    cols = labels[-k:]
    latest, prior = meta["latest_month"], meta["prior_month"]
    ttm_head = f"TTM ({meta['ttm_window']})" if meta["ttm_available"] else "TTM (n/a: <12 months)"
    out = []
    out.append(f"# Monthly trend analysis: {meta['company']}, {latest}")
    out.append("")
    out.append(f"> **DRAFT for reviewer.** Generated {meta['generated_at']} from `{meta['source_file']}` "
               f"(sheets: {meta['sheets']['income_statement']}"
               + (f", {meta['sheets']['balance_sheet']}" if meta['sheets']['balance_sheet'] else "") + "). "
               f"{len(labels)} months ({labels[0]} to {latest}). Figures are as exported ({meta['units']}); "
               "negatives in parentheses. Nothing here is a forecast or an accounting judgment.")
    if meta["partial_months"]:
        out.append(f">\n> ⚠ Partial month(s) in the export: {', '.join(meta['partial_months'])}.")
    dq_bad = [c for c in a["data_quality"]["checks"] if c["status"] == "mismatch"]
    out.append(f">\n> Data-quality checks: **{'ALL PASS' if not dq_bad else f'{len(dq_bad)} MISMATCH(ES), see section 8'}**.")
    out.append("")

    # 1. Commentary
    out.append("## 1. Commentary (draft)")
    out.append("")
    out.append(NARRATIVE_MARKER)
    out.append("")
    out.append("### Flags raised by the rules (evidence for the commentary)")
    out.append("")
    order = {"high": 0, "medium": 1, "info": 2}
    for f in sorted(a["flags"], key=lambda f: order.get(f["severity"], 3)):
        out.append(f"- **[{f['severity']}] {f['kind']}**: {f['message']}")
    out.append("")

    # 2. Revenue
    rev = a["revenue"]
    out.append("## 2. Revenue by stream")
    out.append("")
    rows = []
    for s in rev["streams"] + [rev["total"]]:
        name = f"**{s['name']}**" if s is rev["total"] else s["name"]
        share = (s["ttm"] / rev["total"]["ttm"] * 100) if (s["ttm"] is not None and rev["total"]["ttm"]) else None
        rows.append([name, *[money(v) for v in s["monthly"][-k:]], mom_cell(s), pct(s["yoy_pct"]), money(s["ttm"]),
                     pct(share, False)])
    out.append(_table(["Stream", *cols, f"MoM % ({latest})", "YoY % (same month)", ttm_head, "TTM share"], rows))
    out.append("")
    out.append("Month-over-month % by stream:")
    out.append("")
    rows = []
    for s in rev["streams"] + [rev["total"]]:
        series = _mom_series(s["monthly"])[-k:]
        rows.append([s["name"], *[pct(v) for v in series]])
    out.append(_table(["Stream", *cols], rows))
    out.append("")

    # 3. Gross margin
    gm = a["gross_margin"]
    out.append("## 3. Gross margin trend")
    out.append("")
    rows = []
    prev = None
    for row, ttm in zip(gm["monthly"], gm["ttm_monthly"]):
        pp = None if (prev is None or row["gm_pct"] is None) else row["gm_pct"] - prev
        rows.append([row["month"], money(row["revenue"]), money(row["cogs"]), money(row["gross_profit"]),
                     pct(row["gm_pct"], False), "n/a" if pp is None else f"{pp:+.1f} pp", pct(ttm, False)])
        prev = row["gm_pct"]
    out.append(_table(["Month", "Revenue", "COGS", "Gross profit", "GM %", "Δ vs prior", "TTM GM %"], rows))
    out.append("")

    # 4. Opex by category
    ox = a["operating_expenses"]
    out.append("## 4. Operating expenses by category")
    out.append("")
    rows = []
    for c in ox["categories"]:
        name = c["name"] + (" ¹" if c["non_operating"] else "")
        rows.append([name, *[money(v) for v in c["monthly"][-k:]], mom_cell(c), money(c["ttm"])])
    for t in (ox["underlying"], ox["total"]):
        rows.append([f"**{t['name']}**", *[money(v) for v in t["monthly"][-k:]], mom_cell(t), money(t["ttm"])])
    out.append(_table(["Category", *cols, f"MoM % ({latest})", ttm_head], rows))
    out.append("")
    out.append("¹ Non-operating items that this export places inside operating expenses (tax, interest). Shown separately "
               "so one-off credits do not distort underlying opex; whether to reclassify them is the reviewer's call.")
    out.append("")
    out.append("% changes use the absolute prior value as the base. For credit (negative) lines a positive % means "
               "*less negative*: read the Change column in section 5 for those.")
    out.append("")
    if ox["fallback_accounts"]:
        out.append(f"Accounts in **{ox['fallback_category']}** (no category rule matched; extend `category_map.json` to "
                   f"classify them): {', '.join(ox['fallback_accounts'])}.")
        out.append("")

    # 5. Movers
    mv = a["movers"]
    out.append(f"## 5. Largest movers: {latest} vs {prior}")
    out.append("")
    out.append(_table(["Category", prior, latest, "Change", "MoM %"],
                      [[c["name"], money(c["prior"]), money(c["latest"]), money(c["mom_abs"]), mom_cell(c)] for c in mv["categories"]]))
    out.append("")
    out.append(_table(["Account", "Category", prior, latest, "Change", "MoM %"],
                      [[x["name"], x["category"], money(x["prior"]), money(x["latest"]), money(x["mom_abs"]), mom_cell(x)]
                       for x in mv["accounts"]], ["---", "---", "---:", "---:", "---:", "---:"]))
    out.append("")

    # 6. Net income
    ni = a["net_income"]
    out.append("## 6. Net income")
    out.append("")
    rows = [["Net income (as exported)", *[money(v) for v in ni["monthly"][-k:]], money(ni["ttm"])],
            ["Net income excl. non-operating items", *[money(v) for v in ni["underlying_monthly"][-k:]], money(ni["underlying_ttm"])]]
    out.append(_table(["", *cols, ttm_head], rows))
    out.append("")
    out.append(f"Negative in {ni['negative_months']} of {len(labels)} months; current negative streak: "
               f"{ni['negative_streak_months']} month(s). Positive months: {', '.join(ni['positive_months']) or 'none'}.")
    out.append("")

    # 7. Balance sheet
    bs = a["balance_sheet"]
    out.append("## 7. Balance sheet snapshot")
    out.append("")
    if bs and bs["lines"]:
        rows = [[l["name"], money(l["six_months_earlier"]), money(l["prior"]), money(l["latest"])] for l in bs["lines"].values()]
        out.append(_table(["Line", "6 months earlier", prior, latest], rows))
    else:
        out.append("No balance sheet found in the workbook (optional).")
    out.append("")

    # 8. Data quality
    out.append("## 8. Data quality")
    out.append("")
    out.append(_table(["Check", "Status", "Detail"],
                      [[c["check"], c["status"].upper(), c["detail"]] for c in a["data_quality"]["checks"]], ["---", "---", "---"]))
    out.append("")
    if a["data_quality"]["warnings"]:
        out.append("Extraction warnings:")
        out.append("")
        for w in a["data_quality"]["warnings"]:
            out.append(f"- `{w['type']}`: {w['detail']}")
        out.append("")

    # 9. Mapping appendix
    out.append("## 9. How each expense account was categorised")
    out.append("")
    out.append("<details><summary>Account → category (click to expand)</summary>")
    out.append("")
    out.append(_table(["Account", "Category", "Matched on", f"{latest}", "TTM"],
                      [[x["name"], x["category"], x["matched_on"], money(x["latest"]), money(x["ttm"])] for x in ox["accounts"]],
                      ["---", "---", "---", "---:", "---:"]))
    out.append("")
    out.append("</details>")
    out.append("")

    # 10. Reviewer
    out.append("## 10. For the reviewer")
    out.append("")
    out.append("This report does **not**: " + "; ".join(a["not_done"]) + ".")
    out.append("")
    out.append("- [ ] Confirm the data-quality section (any mismatch: which number is right?)")
    out.append("- [ ] Decide how to treat flagged one-off / non-operating items")
    out.append("- [ ] Check the 'Other' category assignments and the account mapping appendix")
    out.append("- [ ] Add business context the numbers cannot show (pricing changes, churn, hires, timing)")
    out.append("- [ ] Edit the commentary and remove the DRAFT banner when final")
    out.append("")
    return "\n".join(out)
