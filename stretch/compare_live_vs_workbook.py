#!/usr/bin/env python
"""Compare the skill's LIVE run (QuickBooks sandbox, via MCP) with its WORKBOOK run, month by month (stretch goal, D-62).

    python stretch/compare_live_vs_workbook.py [--workbook JSON] [--live JSON]

For every month: total revenue and each revenue stream, COGS, gross profit, gross margin %, operating expenses (the
engine's "Total operating expenses (as exported)") and each expense category, and net income. Tolerance: 0.01 for
amounts, 0.0001 points for percentages. Writes demo-output/stretch/comparison.md and exits 1 on any difference.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT  # noqa: E402

TOL, TOL_PCT = 0.01, 0.0001


def series(a):
    """{metric name: [monthly values]} from one run's JSON."""
    gm = a["gross_margin"]["monthly"]
    out = {"Total revenue": a["revenue"]["total"]["monthly"],
           "COGS": [m["cogs"] for m in gm], "Gross profit": [m["gross_profit"] for m in gm],
           "Gross margin %": [m["gm_pct"] for m in gm],
           a["operating_expenses"]["total"]["name"]: a["operating_expenses"]["total"]["monthly"],
           "Net income": a["net_income"]["monthly"]}
    out.update({f"Stream: {s['name']}": s["monthly"] for s in a["revenue"]["streams"] if any(s["monthly"])})
    out.update({f"Category: {c['name']}": c["monthly"] for c in a["operating_expenses"]["categories"]})
    return out


def compare(wb, live):
    months = wb["meta"]["months"]
    if live["meta"]["months"] != months:
        return months, {}, [f"months differ: workbook {months[0]}..{months[-1]}, live "
                            f"{live['meta']['months'][0]}..{live['meta']['months'][-1]}"]
    a, b = series(wb), series(live)
    problems, worst = [], {}
    for name in sorted(set(a) | set(b)):
        if name not in a or name not in b:
            problems.append(f"{name}: only in the {'live' if name in b else 'workbook'} run")
            continue
        tol = TOL_PCT if name.endswith("%") else TOL
        diffs = [abs((x or 0) - (y or 0)) for x, y in zip(a[name], b[name])]
        worst[name] = max(diffs)
        problems += [f"{name} {months[i]}: workbook {a[name][i]} vs live {b[name][i]}"
                     for i, d in enumerate(diffs) if d > tol]
    return months, worst, problems


def table(wb, live):
    a, b = series(wb), series(live)
    opex = wb["operating_expenses"]["total"]["name"]
    head = ("| Month | Revenue (workbook) | Revenue (live) | GM % (workbook) | GM % (live) | Opex (workbook) | "
            "Opex (live) | Net income (workbook) | Net income (live) | Max difference |")
    lines = [head, "|---|" + "---:|" * 9]
    for i, m in enumerate(wb["meta"]["month_labels"]):
        diff = max(abs(a[k][i] - b[k][i]) for k in ("Total revenue", "Gross margin %", opex, "Net income"))
        lines.append(f"| {m} | {a['Total revenue'][i]:,.2f} | {b['Total revenue'][i]:,.2f} | {a['Gross margin %'][i]:.4f} | "
                     f"{b['Gross margin %'][i]:.4f} | {a[opex][i]:,.2f} | {b[opex][i]:,.2f} | {a['Net income'][i]:,.2f} | "
                     f"{b['Net income'][i]:,.2f} | {diff:.2f} |")
    return "\n".join(lines)


def account_notes(wb, live):
    w = {x["name"] for x in wb["operating_expenses"]["accounts"]}
    l = {x["name"] for x in live["operating_expenses"]["accounts"]}
    zero = sorted(x["name"] for x in wb["operating_expenses"]["accounts"] if not any(x["monthly"]))
    return sorted(w - l), sorted(l - w), zero


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workbook", default=str(OUT / "workbook-run" / "abc-inc-2026-06-trends.json"))
    ap.add_argument("--live", default=None, help="default: the *-trends.json in demo-output/stretch/live-run/")
    args = ap.parse_args(argv)
    wb = json.loads(Path(args.workbook).read_text(encoding="utf-8"))
    live_path = Path(args.live) if args.live else next((OUT / "live-run").glob("*-trends.json"))
    live = json.loads(live_path.read_text(encoding="utf-8"))
    months, worst, problems = compare(wb, live)
    only_wb, only_live, zero = account_notes(wb, live)
    md = [f"# Live (QuickBooks sandbox via MCP) vs workbook run: {len(months)} months, {months[0]} to {months[-1]}", "",
          table(wb, live), "",
          f"**Metrics compared each month:** {len(worst)} (totals, every revenue stream, every expense category). "
          f"Tolerance {TOL} for amounts, {TOL_PCT} for percentages. **Differences beyond tolerance: {len(problems)}.**",
          "", "| Metric | Largest monthly difference |", "|---|---:|"]
    md += [f"| {k} | {v:.4f} |" for k, v in worst.items()]
    md += ["", "**Account-level differences (no effect on any total):**",
           f"- Only in the workbook run: {', '.join(only_wb) or 'none'}",
           f"- Only in the live run: {', '.join(only_live) or 'none'}",
           f"- Zero in every month in the workbook (not loaded, so absent live): {', '.join(zero) or 'none'}"]
    if problems:
        md += ["", "**Differences beyond tolerance:**"] + [f"- {p}" for p in problems]
    (OUT / "comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
