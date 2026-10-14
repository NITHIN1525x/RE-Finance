#!/usr/bin/env python
"""Adapter (stretch goal, D-62): QuickBooks P&L report JSON (as returned by the MCP server) -> a QuickBooks-style
"Profit and Loss" workbook the UNCHANGED skill can read.

    python stretch/pnl_to_workbook.py [--title "ABC Inc (live QBO sandbox)"]

Reads demo-output/stretch/live/pnl-*.json (6-month chunks, by month, class-filtered), merges the month columns and
writes demo-output/stretch/live/abc-live-pnl.xlsx. It lays out exactly what QuickBooks returned, in order:
section headers (no values), account rows, and QuickBooks' OWN "Total …" / "Gross Profit" / "Net Income" rows.
A parent account with postings of its own (ABC's "Marketing/Advertising") comes back as a section whose HEADER carries
those amounts; they are written as a same-name account row right under the header, as in the source workbook.
It adds no rows and computes no numbers; a month an account doesn't appear in is left blank (QuickBooks omits zero rows).
P&L only: no balance sheet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, StretchError  # noqa: E402

LIVE = OUT / "live"
DEFAULT_OUT = LIVE / "abc-live-pnl.xlsx"


def month_columns(report):
    """[(index, 'Jan 2025'), ...] for month columns; the Account column and any Total column are excluded."""
    cols = report["Columns"]["Column"]
    out = []
    for i, c in enumerate(cols):
        meta = {m.get("Name"): m.get("Value") for m in c.get("MetaData", [])}
        if i == 0 or meta.get("ColKey") == "total" or c.get("ColTitle") == "Total":
            continue
        out.append((i, c["ColTitle"]))
    return out


def number(text):
    text = (text or "").strip()
    return float(text) if text else None


class Node:
    def __init__(self, kind, label):
        self.kind, self.label = kind, label            # kind: section | data | summary
        self.children, self.values, self.summary_label, self.summary = {}, {}, None, {}
        self.own = {}                                  # a parent account's own amounts (on its section header)

    def child(self, kind, label):
        key = (kind, label)
        if key not in self.children:
            self.children[key] = Node(kind, label)
        return self.children[key]


def merge(node, rows, cols):
    for row in rows:
        if "Header" in row or "Rows" in row or "Summary" in row:
            header = (row.get("Header") or {}).get("ColData") or []
            label = header[0]["value"] if header else (row.get("group") or "")
            sec = node.child("section", label) if header else node.child("summary", label)
            if header:
                sec.own.update({title: number(header[i]["value"]) for i, title in cols if i < len(header)})
            merge(sec, (row.get("Rows") or {}).get("Row") or [], cols)
            summary = (row.get("Summary") or {}).get("ColData") or []
            if summary:
                sec.summary_label = summary[0]["value"]
                sec.summary.update({title: number(summary[i]["value"]) for i, title in cols})
        else:
            data = row.get("ColData") or []
            leaf = node.child("data", data[0]["value"])
            leaf.values.update({title: number(data[i]["value"]) for i, title in cols})


def emit(node, months, out):
    for child in node.children.values():
        if child.kind == "data":
            out.append([child.label] + [child.values.get(m) for m in months])
        elif child.kind == "section":
            out.append([child.label] + [None] * len(months))           # header: label only, no values
            if any(v is not None for v in child.own.values()):            # parent's own postings, as QuickBooks gave them
                out.append([child.label] + [child.own.get(m) for m in months])
            emit(child, months, out)
            if child.summary_label:
                out.append([child.summary_label] + [child.summary.get(m) for m in months])
        else:                                                           # summary-only rows (Gross Profit, Net Income)
            out.append([child.summary_label or child.label] + [child.summary.get(m) for m in months])


def build(reports, title):
    root, months = Node("section", ""), []
    for rep in reports:
        cols = month_columns(rep)
        months += [t for _, t in cols if t not in months]
        merge(root, rep["Rows"]["Row"], cols)
    rows = []
    emit(root, months, rows)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Profit and Loss"
    for line in (title, "Profit and Loss", f"{months[0]} - {months[-1]}", None):
        ws.append([line])
    ws.append([""] + months)
    for r in rows:
        ws.append(r)
    return wb, months, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", default="ABC Inc (live QBO sandbox)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    files = sorted(LIVE.glob("pnl-*.json"))
    if not files:
        print("[stretch] STOPPED: no demo-output/stretch/live/pnl-*.json; run stretch/read_live_pnl.py first",
              file=sys.stderr)
        return 1
    try:
        wb, months, rows = build([json.loads(f.read_text(encoding="utf-8")) for f in files], args.title)
    except StretchError as exc:
        print(f"[stretch] STOPPED: {exc}", file=sys.stderr)
        return 1
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.out)
    print(f"[stretch] {len(files)} chunk(s) -> {len(months)} months ({months[0]} to {months[-1]}), {len(rows)} rows "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
