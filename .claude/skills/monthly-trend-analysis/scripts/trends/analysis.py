"""Turn parsed sheets into a JSON-serialisable analysis dict (the contract the report and the reviewer use).

Numbers come only from the workbook. Nothing here forecasts or makes accounting judgments; flags are
rule-based ("moved more than X%", "new line", "single-month spike") with thresholds from category_map.json.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone
from pathlib import Path

from . import mapping

ROUND = 2


# ----------------------------------------------------------------------------------------------- small helpers
def r2(x):
    return None if x is None else round(x, ROUND)


def r4(x):
    """Percentages keep 4 decimals so a later 1-decimal display rounds once (59.5510 -> 59.6, not 59.55 -> 59.5)."""
    return None if x is None else round(x, 4)


def pct_change(cur, prev):
    """Fractional change; None when the base is 0 (a 'new' value). Uses |prev| so negative bases read sensibly."""
    if prev is None or cur is None or abs(prev) < 1e-9:
        return None
    return (cur - prev) / abs(prev)


def ttm_series(values):
    """Trailing-twelve-month sums; None until 12 months are available."""
    return [None if i < 11 else sum(values[i - 11:i + 1]) for i in range(len(values))]


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def mlabel(d):
    return d.strftime("%b %Y")


def series_block(name, values, months, extra=None):
    """Standard per-line block: monthly values, latest/prior, MoM, TTM."""
    ttm = ttm_series(values)
    latest, prior = values[-1], (values[-2] if len(values) > 1 else None)
    block = {
        "name": name,
        "monthly": [r2(v) for v in values],
        "latest": r2(latest),
        "prior": r2(prior),
        "mom_abs": r2(latest - prior) if prior is not None else None,
        "mom_pct": r4(pct_change(latest, prior) * 100) if pct_change(latest, prior) is not None else None,
        "ttm": r2(ttm[-1]),
        "ttm_prior_month": r2(ttm[-2]) if len(ttm) > 1 else None,
        "ttm_monthly": [r2(v) for v in ttm],
        # Same month last year (needs >= 13 months). Guards against reading seasonality as a trend.
        "same_month_last_year": r2(values[-13]) if len(values) >= 13 else None,
        "yoy_pct": (r4(pct_change(latest, values[-13]) * 100)
                    if len(values) >= 13 and pct_change(latest, values[-13]) is not None else None),
    }
    if extra:
        block.update(extra)
    return block


# ----------------------------------------------------------------------------------------------- main entry
def analyze(income_sheet, balance_sheet, config, source_file, company=None):
    th = config["thresholds"]
    months = income_sheet.months
    n = len(months)
    if n < 2:
        raise ValueError("At least two months are required for a month-over-month analysis")
    flags, checks = [], []

    # ---- statement roles for top-level income-statement sections
    roles = {"revenue": [], "cogs": [], "operating_expenses": [], "other_income": [], "other_expense": []}
    for sec in income_sheet.sections:
        role = mapping.section_role(sec.name, config)
        if role is None:
            flags.append(_flag("high", "data_quality", f"Top-level section '{sec.name}' is not recognised as revenue, "
                               "COGS, operating expenses or other income/expense; it is listed but excluded from margins. "
                               "Add a pattern to statement_sections in category_map.json."))
            roles.setdefault("unclassified", []).append(sec)
        else:
            roles[role].append(sec)

    def lines(role):
        out = []
        for sec in roles.get(role, []):
            for acc, path in sec.accounts():
                out.append((acc, path[1:]))   # drop the top-level section name from the group path
        return out

    zero = [0.0] * n
    rev_lines, cogs_lines, opex_lines = lines("revenue"), lines("cogs"), lines("operating_expenses")
    oi_lines, oe_lines = lines("other_income"), lines("other_expense")
    total_rev = sum_lines(rev_lines, n)
    total_cogs = sum_lines(cogs_lines, n)
    gross_profit = [a - b for a, b in zip(total_rev, total_cogs)]
    total_opex = sum_lines(opex_lines, n)
    other_net = [a - b for a, b in zip(sum_lines(oi_lines, n), sum_lines(oe_lines, n))]
    net_income = [g - o + x for g, o, x in zip(gross_profit, total_opex, other_net)]

    # ---- revenue streams
    streams = [series_block(acc.name, acc.values, months, {"group": " > ".join(p) or None}) for acc, p in rev_lines]
    rev_total = series_block("Total revenue", total_rev, months)

    # ---- gross margin
    gm_pct = [(g / r * 100) if abs(r) > 1e-9 else None for g, r in zip(gross_profit, total_rev)]
    ttm_rev, ttm_gp = ttm_series(total_rev), ttm_series(gross_profit)
    gm_ttm = [(g / r * 100) if (r and g is not None) else None for g, r in zip(ttm_gp, ttm_rev)]
    gross_margin = {
        "monthly": [{"month": m.isoformat()[:7], "revenue": r2(r), "cogs": r2(c), "gross_profit": r2(g), "gm_pct": r4(p)}
                    for m, r, c, g, p in zip(months, total_rev, total_cogs, gross_profit, gm_pct)],
        "ttm_gm_pct": r4(gm_ttm[-1]),
        "ttm_gm_pct_prior_month": r4(gm_ttm[-2]),
        "ttm_monthly": [r4(v) for v in gm_ttm],
        "cogs_lines": [series_block(acc.name, acc.values, months) for acc, _ in cogs_lines],
    }

    # ---- operating expenses by category
    cat_values, cat_accounts, cat_nonop, account_blocks = {}, {}, {}, []
    for acc, groups in opex_lines:
        cat, nonop, why = mapping.opex_category(acc.name, groups, config)
        cat_values[cat] = add(cat_values.get(cat, zero), acc.values)
        cat_accounts.setdefault(cat, []).append(acc.name)
        cat_nonop[cat] = nonop
        account_blocks.append(series_block(acc.name, acc.values, months, {
            "category": cat, "non_operating": nonop, "matched_on": why, "group": " > ".join(groups) or None,
            "blank_months": acc.blank_months}))
    categories = sorted(
        (series_block(cat, vals, months, {"non_operating": cat_nonop[cat], "accounts": cat_accounts[cat]})
         for cat, vals in cat_values.items()),
        key=lambda b: -abs(b["ttm"] if b["ttm"] is not None else b["latest"]))
    nonop_values = sum_lines([(a, g) for a, g in opex_lines if mapping.opex_category(a.name, g, config)[1]], n)
    underlying_opex = [t - x for t, x in zip(total_opex, nonop_values)]
    fallback = config["opex_categories"]["fallback_category"]
    opex = {
        "categories": categories,
        "accounts": account_blocks,
        "total": series_block("Total operating expenses (as exported)", total_opex, months),
        "underlying": series_block("Operating expenses excl. non-operating items", underlying_opex, months),
        "fallback_category": fallback,
        "fallback_accounts": cat_accounts.get(fallback, []),
    }

    # ---- net income
    underlying_ni = [ni + x for ni, x in zip(net_income, nonop_values)]
    streak = 0
    for v in reversed(net_income):
        if v < 0:
            streak += 1
        else:
            break
    ni = series_block("Net income", net_income, months, {
        "negative_streak_months": streak,
        "negative_months": sum(1 for v in net_income if v < 0),
        "positive_months": [mlabel(m) for m, v in zip(months, net_income) if v >= 0],
        "underlying_monthly": [r2(v) for v in underlying_ni],
        "underlying_ttm": r2(ttm_series(underlying_ni)[-1]),
    })

    # ---- cross-checks against the workbook's own summary rows
    stated = {}
    for row in income_sheet.summaries:
        role = mapping.summary_role(row.name, config)
        if role and role not in stated:
            stated[role] = row
    for role, computed in (("gross_profit", gross_profit), ("net_income", net_income),
                           ("operating_income", [g - o for g, o in zip(gross_profit, total_opex)])):
        row = stated.get(role)
        if row is None:
            checks.append({"check": f"{role} vs workbook", "status": "skipped", "detail": "no such summary row in the sheet"})
            continue
        diffs = [(mlabel(m), s - c) for m, s, c in zip(months, row.values, computed) if abs(s - c) > 0.01]
        checks.append({"check": f"{role} recomputed from detail rows vs workbook '{row.name}'",
                       "status": "pass" if not diffs else "mismatch",
                       "detail": "matches in every month" if not diffs else
                       "; ".join(f"{m}: workbook - recomputed = {d:,.2f}" for m, d in diffs[:6])})
    subtotal_mismatches = [w for w in income_sheet.warnings if w["type"] == "subtotal_mismatch"]
    checks.insert(0, {"check": "every stated subtotal vs sum of its detail rows (income statement)",
                      "status": "pass" if not subtotal_mismatches else "mismatch",
                      "detail": f"{_count_totals(income_sheet)} subtotal rows x {n} months checked; "
                                f"{len(subtotal_mismatches)} mismatches"})

    # ---- balance sheet (optional)
    bs = analyze_balance_sheet(balance_sheet, months, config, checks) if balance_sheet is not None else None

    # ---- flags (rule-based; Claude turns these into prose, the reviewer decides what they mean)
    materiality = max(th["materiality_abs"], th["materiality_pct_of_revenue"] * _avg(total_rev))
    lb = min(th["lookback_months"], n - 1)
    latest, prior = mlabel(months[-1]), mlabel(months[-2])
    _flag_revenue(flags, rev_total, streams, months, th, lb, materiality)
    _flag_margin(flags, gm_pct, months, th, lb)
    _flag_opex(flags, categories, account_blocks, months, th, lb, materiality)
    _flag_spikes(flags, account_blocks + streams, months, th, materiality)
    _flag_net_income(flags, ni, net_income, underlying_ni, months, account_blocks)
    if bs:
        _flag_balance_sheet(flags, bs, months, materiality)
    if months[-1] in income_sheet.partial_months:
        flags.insert(0, _flag("high", "data_quality", f"{latest} is a partial month in the export; MoM comparisons understate it."))
    for w in income_sheet.warnings + (balance_sheet.warnings if balance_sheet is not None else []):
        flags.append(_flag("high" if w["type"] in ("subtotal_mismatch", "unmatched_total") else "info",
                           "data_quality", w["detail"]))

    movers = {
        "categories": sorted([c for c in categories if c["mom_abs"]], key=lambda c: -abs(c["mom_abs"]))[: th["top_movers"]],
        "accounts": sorted([a for a in account_blocks if a["mom_abs"]], key=lambda a: -abs(a["mom_abs"]))[: th["top_movers"]],
    }
    if fallback in cat_values:
        flags.append(_flag("info", "mapping", f"{len(cat_accounts[fallback])} expense account(s) matched no category rule and "
                           f"are grouped as '{fallback}': {', '.join(cat_accounts[fallback])}."))

    return {
        "meta": {
            "company": company or _company_from_titles(income_sheet.title_lines),
            "source_file": Path(str(source_file)).name,   # file name only: no local folders in shared outputs
            "sheets": {"income_statement": income_sheet.title,
                       "balance_sheet": balance_sheet.title if balance_sheet is not None else None},
            "title_lines": income_sheet.title_lines,
            "months": [m.isoformat()[:7] for m in months],
            "month_labels": [mlabel(m) for m in months],
            "latest_month": latest,
            "prior_month": prior,
            "ttm_window": f"{mlabel(months[-12])} - {latest}" if n >= 12 else None,
            "ttm_available": n >= 12,
            "partial_months": [mlabel(m) for m in income_sheet.partial_months],
            "materiality": r2(materiality),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "units": "currency as exported (no conversion)",
        },
        "revenue": {"total": rev_total, "streams": streams},
        "gross_margin": gross_margin,
        "operating_expenses": opex,
        "net_income": ni,
        "balance_sheet": bs,
        "movers": movers,
        "flags": flags,
        "data_quality": {"checks": checks,
                         "warnings": income_sheet.warnings + (balance_sheet.warnings if balance_sheet is not None else [])},
        "not_done": ["forecasting", "accounting judgments (accruals, reclassifications, one-off treatment)",
                     "currency conversion", "causal explanations beyond what the numbers show"],
    }


# ----------------------------------------------------------------------------------------------- pieces
def sum_lines(lines, n):
    out = [0.0] * n
    for acc, _ in lines:
        out = add(out, acc.values)
    return out


def _avg(values):
    return sum(values) / len(values) if values else 0.0


def _count_totals(sheet):
    count = 0

    def walk(sec):
        nonlocal count
        count += sec.stated_total is not None
        for c in sec.children:
            if hasattr(c, "children"):
                walk(c)
    for s in sheet.sections:
        walk(s)
    return count


def _company_from_titles(lines):
    # QBO exports: [report title, company name, period line]. Fall back to the first line.
    candidates = [l for l in lines if not any(k in l.lower() for k in
                  ("statement", "profit and loss", "balance sheet", "for the", "as at", "as of", "month", "period"))]
    return candidates[0] if candidates else (lines[0] if lines else "Unknown company")


def _flag(severity, kind, message, **figures):
    return {"severity": severity, "kind": kind, "message": message, **({"figures": figures} if figures else {})}


def _flag_revenue(flags, total, streams, months, th, lb, materiality):
    latest, prior = mlabel(months[-1]), mlabel(months[-2])
    vals = total["monthly"]
    avg_prev = _avg(vals[-1 - lb:-1])
    vs_avg = pct_change(vals[-1], avg_prev)
    yoy = (f"; {total['yoy_pct']:+.1f}% vs {mlabel(months[-13])} ({total['same_month_last_year']:,.0f})"
           if total["yoy_pct"] is not None else "")
    if total["mom_pct"] is not None and abs(total["mom_pct"]) >= th["revenue_mom_pct"] * 100:
        flags.append(_flag("high", "revenue",
                           f"Total revenue {latest}: {vals[-1]:,.0f}, {total['mom_pct']:+.1f}% vs {prior} ({vals[-2]:,.0f})"
                           + (f", {vs_avg * 100:+.1f}% vs the prior {lb}-month average ({avg_prev:,.0f})" if vs_avg is not None else "")
                           + yoy + ".",
                           latest=vals[-1], prior=vals[-2], mom_pct=total["mom_pct"], prior_avg=r2(avg_prev),
                           yoy_pct=total["yoy_pct"]))
        if vals[-2] == max(vals[:-1]):
            flags.append(_flag("info", "revenue", f"{prior} ({vals[-2]:,.0f}) was the highest month in the export, so the "
                               f"{latest} month-over-month change is measured from a peak."))
    elif vs_avg is not None and abs(vs_avg) >= th["revenue_mom_pct"]:
        flags.append(_flag("medium", "revenue", f"Total revenue {latest} is {vs_avg * 100:+.1f}% vs the prior {lb}-month average "
                           f"({avg_prev:,.0f}) although only {total['mom_pct']:+.1f}% vs {prior}."))
    for s in streams:
        v = s["monthly"]
        window = v[-1 - lb:-1]
        if s["mom_pct"] is not None and abs(s["mom_pct"]) >= th["stream_mom_pct"] * 100 and abs(s["mom_abs"]) >= materiality:
            flags.append(_flag("medium", "revenue_stream", f"Revenue stream '{s['name']}' {latest}: {v[-1]:,.0f} "
                               f"({s['mom_pct']:+.1f}% / {s['mom_abs']:+,.0f} vs {prior})."))
        if abs(v[-1]) >= materiality and all(abs(x) < 0.005 for x in window):
            flags.append(_flag("medium", "revenue_stream", f"New revenue stream '{s['name']}': {v[-1]:,.0f} in {latest}, "
                               f"zero in the prior {lb} months."))
        if abs(v[-1]) < 0.005 and any(abs(x) >= materiality for x in window):
            last_nz = next(i for i in range(len(v) - 2, -1, -1) if abs(v[i]) >= 0.005)   # exists: window has a material month
            when = (f"is zero in {latest}" if last_nz == len(v) - 2 else
                    f"has been zero since {mlabel(months[last_nz + 1])} (last non-zero: {mlabel(months[last_nz])}, {v[last_nz]:,.0f})")
            flags.append(_flag("medium", "revenue_stream", f"Revenue stream '{s['name']}' {when} after "
                               f"{max(window, key=abs):,.0f} at its peak in the prior {lb} months."))
        negatives = [(mlabel(m), x) for m, x in zip(months, v) if x < 0]
        if negatives:
            flags.append(_flag("medium", "revenue_stream", f"Revenue stream '{s['name']}' is negative in "
                               + ", ".join(f"{m} ({x:,.0f})" for m, x in negatives)
                               + ": likely credits/refunds; reviewer to confirm."))
        first, last = v[0], v[-1]
        if len(v) >= 6 and abs(first) >= materiality and pct_change(last, first) is not None and abs(pct_change(last, first)) >= 0.4:
            flags.append(_flag("info", "revenue_stream", f"Revenue stream '{s['name']}' moved from {first:,.0f} "
                               f"({mlabel(months[0])}) to {last:,.0f} ({latest}), {pct_change(last, first) * 100:+.0f}% over the period."))


def _flag_margin(flags, gm, months, th, lb):
    latest, prior = mlabel(months[-1]), mlabel(months[-2])
    if gm[-1] is None:
        return
    window = [g for g in gm[-1 - lb:-1] if g is not None]
    avg = _avg(window)
    delta_prior = gm[-1] - gm[-2] if gm[-2] is not None else None
    if window and gm[-1] < avg - th["gross_margin_pp"]:
        flags.append(_flag("high", "gross_margin", f"Gross margin compression: {latest} {gm[-1]:.1f}% vs {avg:.1f}% average "
                           f"over the prior {lb} months ({prior}: {gm[-2]:.1f}%)."))
    elif delta_prior is not None and abs(delta_prior) >= th["gross_margin_pp"]:
        flags.append(_flag("medium", "gross_margin", f"Gross margin {latest} {gm[-1]:.1f}% vs {gm[-2]:.1f}% in {prior} "
                           f"({delta_prior:+.1f} pp); prior {lb}-month average {avg:.1f}%."))
    if len(gm) >= 13 and gm[-13] is not None:
        flags.append(_flag("info", "gross_margin", f"Gross margin {latest} {gm[-1]:.1f}% vs {gm[-13]:.1f}% in "
                           f"{mlabel(months[-13])} ({gm[-1] - gm[-13]:+.1f} pp year over year)."))
    valid = [(m, g) for m, g in zip(months, gm) if g is not None]
    lo, hi = min(valid, key=lambda t: t[1]), max(valid, key=lambda t: t[1])
    flags.append(_flag("info", "gross_margin", f"Gross margin range over the period: {lo[1]:.1f}% ({mlabel(lo[0])}) to "
                       f"{hi[1]:.1f}% ({mlabel(hi[0])})."))


def _flag_opex(flags, categories, accounts, months, th, lb, materiality):
    latest, prior = mlabel(months[-1]), mlabel(months[-2])
    for c in categories:
        if c["mom_pct"] is not None and abs(c["mom_pct"]) >= th["category_mom_pct"] * 100 and abs(c["mom_abs"]) >= materiality:
            flags.append(_flag("medium", "opex_category", f"Opex category '{c['name']}' {latest}: {c['latest']:,.0f} "
                               f"({c['mom_pct']:+.1f}% / {c['mom_abs']:+,.0f} vs {prior})."))
    for a in accounts:
        v = a["monthly"]
        window = v[-1 - lb:-1]
        if abs(v[-1]) >= materiality and all(abs(x) < 0.005 for x in window):
            flags.append(_flag("medium", "new_expense_line", f"New expense line '{a['name']}' ({a['category']}): "
                               f"{v[-1]:,.0f} in {latest}, zero in the prior {lb} months."))
        elif abs(v[-1]) < 0.005 and sum(1 for x in window if abs(x) >= materiality) >= 2:
            last_nz = next(i for i in range(len(v) - 2, -1, -1) if abs(v[i]) >= 0.005)   # exists: window has >= 2 material months
            if last_nz == len(v) - 2:      # non-zero last month: it really went to zero in the latest month
                when = f"is zero in {latest}"
            else:                          # already zero before the latest month: say since when, and the last non-zero
                when = (f"has been zero since {mlabel(months[last_nz + 1])} "
                        f"(last non-zero: {mlabel(months[last_nz])}, {v[last_nz]:,.0f})")
            flags.append(_flag("medium", "vanished_expense_line", f"Expense line '{a['name']}' ({a['category']}) {when}; "
                               f"it averaged {_avg(window):,.0f} over the prior {lb} months."))


def _flag_spikes(flags, blocks, months, th, materiality):
    spikes = []
    for b in blocks:
        v = b["monthly"]
        for i, x in enumerate(v):
            others = [abs(y) for j, y in enumerate(v) if j != i]
            if i == len(v) - 1 and all(abs(y) < 0.005 for y in others):
                continue   # only non-zero in the latest month: that is a "new line", flagged elsewhere
            med = statistics.median(others) if others else 0
            if abs(x) >= materiality * 5 and abs(x) >= th["spike_multiple_of_median"] * max(med, materiality):
                spikes.append((abs(x), b["name"], mlabel(months[i]), x, med, b.get("category")))
    spikes.sort(reverse=True)
    for _, name, m, x, med, cat in spikes[:6]:
        flags.append(_flag("high" if abs(x) >= 20 * materiality else "medium", "one_off",
                           f"Single-month spike: '{name}'{f' ({cat})' if cat else ''} is {x:,.0f} in {m} vs a typical "
                           f"(median) month of {med:,.0f}. Reviewer to decide whether it is one-off."))
    if len(spikes) > 6:
        flags.append(_flag("info", "one_off", f"{len(spikes) - 6} smaller single-month spikes not listed (see accounts table)."))


def _flag_net_income(flags, ni, values, underlying, months, accounts):
    latest = mlabel(months[-1])
    if ni["negative_streak_months"]:
        flags.append(_flag("high", "net_income", f"Net income is negative for {ni['negative_streak_months']} consecutive months "
                           f"through {latest} ({values[-1]:,.0f} in {latest}; TTM {ni['ttm']:,.0f})."
                           if ni["ttm"] is not None else
                           f"Net income is negative for {ni['negative_streak_months']} consecutive months through {latest}."))
    for m, v, u in zip(months, values, underlying):
        if v >= 0 > u:
            drivers = sorted((a for a in accounts if a["non_operating"]), key=lambda a: a["monthly"][months.index(m)])
            top = drivers[0] if drivers else None
            flags.append(_flag("high", "net_income", f"{mlabel(m)} shows positive net income ({v:,.0f}) only because of "
                               f"non-operating items; excluding them it is {u:,.0f}"
                               + (f" (largest: '{top['name']}' {top['monthly'][months.index(m)]:,.0f})." if top else ".")))


def _flag_balance_sheet(flags, bs, months, materiality):
    """Movement only. No runway or burn projection: that is forecasting and belongs to the reviewer."""
    cash = bs["lines"].get("cash")
    if not cash or cash["prior"] is None:
        return
    latest = mlabel(months[-1])
    mom = cash["latest"] - cash["prior"]
    six = cash["latest"] - cash["six_months_earlier"] if cash["six_months_earlier"] is not None else 0
    if abs(mom) >= materiality * 10 or abs(six) >= materiality * 10:
        flags.append(_flag("high" if min(mom, six) < 0 else "medium", "cash",
                           f"'{cash['name']}' {latest}: {cash['latest']:,.0f}, {mom:+,.0f} vs prior month"
                           + (f" and {cash['latest'] - cash['six_months_earlier']:+,.0f} vs six months earlier "
                              f"({cash['six_months_earlier']:,.0f})." if cash["six_months_earlier"] is not None else ".")))


def analyze_balance_sheet(sheet, months, config, checks):
    idx = {m: i for i, m in enumerate(sheet.months)}
    common = [m for m in months if m in idx]
    found = {}

    def walk(sec):
        role = mapping.balance_role(sec.name, config)
        if role and role not in found and sec.stated_total is not None:
            found[role] = sec
        for c in sec.children:
            if hasattr(c, "children"):
                walk(c)
    for s in sheet.sections:
        walk(s)
    out = {"months": [m.isoformat()[:7] for m in common], "lines": {}}
    for role, sec in found.items():
        vals = [sec.stated_total[idx[m]] for m in common]
        out["lines"][role] = {"name": sec.name, "monthly": [r2(v) for v in vals], "latest": r2(vals[-1]),
                              "prior": r2(vals[-2]) if len(vals) > 1 else None,
                              "six_months_earlier": r2(vals[-7]) if len(vals) > 6 else None}
    a, le = found.get("total_assets"), found.get("liabilities_and_equity")
    if a is None and sheet.sections:
        a = sheet.sections[0]
    if le is None and len(sheet.sections) > 1:
        le = sheet.sections[-1]
    if a is not None and le is not None and a.stated_total and le.stated_total:
        diffs = [(mlabel(m), a.stated_total[idx[m]] - le.stated_total[idx[m]]) for m in common
                 if abs(a.stated_total[idx[m]] - le.stated_total[idx[m]]) > 0.01]
        checks.append({"check": f"balance sheet: '{a.name}' = '{le.name}'", "status": "pass" if not diffs else "mismatch",
                       "detail": "balances in every month" if not diffs else "; ".join(f"{m}: {d:,.2f}" for m, d in diffs[:6])})
    bs_mismatch = [w for w in sheet.warnings if w["type"] == "subtotal_mismatch"]
    checks.append({"check": "every stated subtotal vs sum of its detail rows (balance sheet)",
                   "status": "pass" if not bs_mismatch else "mismatch",
                   "detail": f"{_count_totals(sheet)} subtotal rows checked; {len(bs_mismatch)} mismatches"})
    missing = [m for m in months if m not in idx]
    if missing:
        checks.append({"check": "balance sheet covers the income-statement months", "status": "partial",
                       "detail": f"missing: {', '.join(mlabel(m) for m in missing)}"})
    return out
