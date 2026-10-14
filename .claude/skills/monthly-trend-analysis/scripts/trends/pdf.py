"""Render the analysis dict (the skill's *-trends.json) as a printable PDF for the human reviewer.

Rules:
- Every number comes from the analysis dict, formatted with the SAME helpers as the Markdown report
  (report.money / report.pct / report.mom_cell). Nothing is recalculated: margins are shown as stored levels
  (latest, prior month, same month last year, TTM), not as differences computed here.
- The only prose not generated from the JSON is the draft commentary, copied verbatim from the report's section 1
  under a "DRAFT commentary for reviewer" label, and the engine's reviewer checklist (report section 10).
- Missing TTM / YoY is printed as "not available (only N months)"; no chart is drawn from missing values.
- Output is byte-reproducible (ReportLab invariant mode), so rebuilding never creates spurious diffs.
- Built-in PDF fonts only: the two symbols they cannot draw are written as text ("->" for an arrow, "change" for
  the Greek capital delta).
"""
from __future__ import annotations

import math
import re
from pathlib import Path, PureWindowsPath
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.graphics.shapes import Drawing, Group, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from .report import NARRATIVE_MARKER, money, mom_cell, pct

# --------------------------------------------------------------------------------------------- look
INK = colors.HexColor("#17202b")
MUTED = colors.HexColor("#566372")
RULE = colors.HexColor("#c9d1db")
SHADE = colors.HexColor("#eef1f5")
ACCENT = colors.HexColor("#1f3a5f")
DRAFT_BG = colors.HexColor("#fdf1e1")
DRAFT_INK = colors.HexColor("#8a3c08")
# Series fills: distinct lightness steps so stacked bars still separate when printed in black and white.
SERIES = [colors.HexColor(c) for c in ("#1f3a5f", "#7f9cc4", "#3d5a80", "#c4d3e8", "#5f6b7a", "#a3adb8", "#2b2b2b",
                                       "#dde3ea")]
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
FRAME_W = PAGE_W - 2 * MARGIN

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12, textColor=INK, alignment=TA_LEFT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=9.5, textColor=MUTED)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.5, leading=9.2)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=12.5, leading=16, spaceBefore=6,
                    spaceAfter=4, textColor=ACCENT)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=9, firstLineIndent=-7, spaceAfter=3)
H3 = ParagraphStyle("h3", parent=BODY, fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=4, spaceAfter=2)

SYMBOLS = {"→": "->", "Δ": "change"}


def clean(text):
    """Text safe for the built-in fonts and for Paragraph markup."""
    text = str(text)
    for symbol, replacement in SYMBOLS.items():
        text = text.replace(symbol, replacement)
    return escape(text)


def md_inline(text):
    """**bold** and `code` from the report's Markdown, after escaping."""
    text = clean(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)


# --------------------------------------------------------------------------------------------- data access
def months_note(a):
    return f"not available (only {len(a['meta']['months'])} months)"


def missing(a):
    """What to print for a TTM / YoY value that is None."""
    return months_note(a) if not a["meta"].get("ttm_available", True) else "n/a"


def ttm_cell(a, block, short=False):
    return money(block["ttm"]) if block.get("ttm") is not None else ("n/a" if short else missing(a))


def yoy_cell(a, block, short=False):
    return pct(block["yoy_pct"]) if block.get("yoy_pct") is not None else ("n/a" if short else missing(a))


def gm_level(entry):
    return pct(entry["gm_pct"], signed=False) if entry and entry.get("gm_pct") is not None else "n/a"


def same_month_last_year_gm(a):
    """The stored gross-margin entry for the latest month one year earlier (selected by its label, not computed)."""
    latest = a["gross_margin"]["monthly"][-1]["month"]
    target = f"{int(latest[:4]) - 1}{latest[4:]}"
    return next((m for m in a["gross_margin"]["monthly"] if m["month"] == target), None)


def key_figures(a):
    """Rows for the key-figures table: [label, latest, prior month, MoM, same month last year, YoY, TTM]."""
    rev, opex, ni = a["revenue"]["total"], a["operating_expenses"]["total"], a["net_income"]
    gm = a["gross_margin"]
    smly_gm = same_month_last_year_gm(a)

    def amount_row(label, block):
        smly = block.get("same_month_last_year")
        return [label, money(block["latest"]), money(block["prior"]), mom_cell(block),
                money(smly) if smly is not None else missing(a), yoy_cell(a, block), ttm_cell(a, block)]

    gm_ttm = pct(gm["ttm_gm_pct"], signed=False) if gm.get("ttm_gm_pct") is not None else missing(a)
    return [
        amount_row("Total revenue", rev),
        ["Gross margin %", gm_level(gm["monthly"][-1]), gm_level(gm["monthly"][-2]) if len(gm["monthly"]) > 1 else "n/a",
         "level", gm_level(smly_gm) if smly_gm else missing(a), "level", gm_ttm],
        amount_row(opex["name"], opex),            # the engine's label: "Total operating expenses (as exported)"
        amount_row("Net income", ni),
    ]


def stream_rows(a):
    rows = [[clean(s["name"]), money(s["latest"]), money(s["prior"]), mom_cell(s), yoy_cell(a, s, True),
             ttm_cell(a, s, True)] for s in a["revenue"]["streams"]]
    t = a["revenue"]["total"]
    return rows + [["Total revenue", money(t["latest"]), money(t["prior"]), mom_cell(t), yoy_cell(a, t, True),
                    ttm_cell(a, t, True)]]


def category_rows(a):
    rows = [[clean(c["name"]) + (" (non-operating)" if c.get("non_operating") and "non-operating" not in c["name"]
                                  else ""), money(c["latest"]),
             money(c["prior"]), mom_cell(c), yoy_cell(a, c, True), ttm_cell(a, c, True)]
            for c in a["operating_expenses"]["categories"]]
    t = a["operating_expenses"]["total"]
    return rows + [[clean(t["name"]), money(t["latest"]), money(t["prior"]), mom_cell(t), yoy_cell(a, t, True),
                    ttm_cell(a, t, True)]]


def non_operating_names(a):
    return [c["name"] for c in a["operating_expenses"]["categories"] if c.get("non_operating")]


def mismatch_rows(a):
    label_of = dict(zip(a["meta"]["months"], a["meta"]["month_labels"]))
    return [[clean(w.get("section", "")), label_of.get(w.get("month", ""), w.get("month", "")), money(w["stated"]),
             money(w["detail_sum"]),
             money(w["difference"])]
            for w in a["data_quality"]["warnings"] if w.get("type") == "subtotal_mismatch"]


def report_section(md, start, end=None):
    if not md or start not in md:
        return None
    body = md.split(start, 1)[1]
    if end and end in body:
        body = body.split(end, 1)[0]
    return body.strip()


# --------------------------------------------------------------------------------------------- charts
def nice_ticks(lo, hi, count=5):
    lo, hi = min(lo, 0.0), max(hi, 0.0)
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / count
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(lo / step) * step
    ticks = []
    v = start
    while v <= hi + step * 0.001:
        ticks.append(round(v, 10))
        v += step
    if ticks[-1] < hi:
        ticks.append(ticks[-1] + step)
    return ticks


def tick_label(v, percent=False):
    if percent:
        return f"{v:.0f}%"
    a = abs(v)
    text = f"{a / 1e6:.1f}M" if a >= 1e6 else f"{a / 1e3:.0f}k" if a >= 1e3 else f"{a:.0f}"
    return f"-{text}" if v < 0 else text


def month_axis_labels(labels):
    """Short labels: 'Jan 26'. Shown for every month when it fits, otherwise every other one."""
    short = [f"{l.split()[0]} {l.split()[1][2:]}" if len(l.split()) == 2 else l for l in labels]
    return short, (1 if len(short) <= 12 else 2)


class Plot:
    """Plot area with a value axis, light grid lines and a bold zero line."""

    def __init__(self, width, height, ticks, percent=False, left=34, bottom=26, top=8, right=6):
        self.d = Drawing(width, height)
        self.x0, self.y0 = left, bottom
        self.w, self.h = width - left - right, height - bottom - top
        self.lo, self.hi = ticks[0], ticks[-1]
        for t in ticks:
            y = self.y(t)
            self.d.add(Line(self.x0, y, self.x0 + self.w, y, strokeColor=RULE, strokeWidth=0.4))
            self.d.add(String(self.x0 - 3, y - 2.5, tick_label(t, percent), fontName="Helvetica", fontSize=6,
                              fillColor=MUTED, textAnchor="end"))
        if self.lo <= 0 <= self.hi:   # a percent axis may start above 0: never draw a zero line outside the plot
            self.d.add(Line(self.x0, self.y(0), self.x0 + self.w, self.y(0), strokeColor=INK, strokeWidth=0.9))
        else:
            self.d.add(Line(self.x0, self.y0, self.x0 + self.w, self.y0, strokeColor=MUTED, strokeWidth=0.6))

    def y(self, v):
        return self.y0 + (v - self.lo) / (self.hi - self.lo) * self.h

    def month_labels(self, labels, slot):
        short, every = month_axis_labels(labels)
        for i, text in enumerate(short):
            if i % every == 0 or i == len(short) - 1:
                self.d.add(String(self.x0 + slot * (i + 0.5), self.y0 - 9, text, fontName="Helvetica", fontSize=5.8,
                                  fillColor=MUTED, textAnchor="middle"))


def legend(drawing, items, x, y, max_width):
    """items: [(label, fill or None, dash or None)]; wraps across lines."""
    cx, cy = x, y
    for label, fill, dash in items:
        w = 14 + len(label) * 3.3
        if cx + w > x + max_width:
            cx, cy = x, cy - 9
        if fill is not None:
            drawing.add(Rect(cx, cy - 1, 7, 6, fillColor=fill, strokeColor=INK, strokeWidth=0.3))
        else:
            drawing.add(Line(cx, cy + 2, cx + 9, cy + 2, strokeColor=INK, strokeWidth=1.2, strokeDashArray=dash))
        drawing.add(String(cx + 10, cy, label, fontName="Helvetica", fontSize=6.3, fillColor=INK))
        cx += w + 6


def stacked_revenue_chart(a, width=FRAME_W, height=72 * mm):
    streams = a["revenue"]["streams"]
    labels = a["meta"]["month_labels"]
    n = len(labels)
    pos = [sum(max(s["monthly"][i], 0) for s in streams) for i in range(n)]
    neg = [sum(min(s["monthly"][i], 0) for s in streams) for i in range(n)]
    p = Plot(width, height - 22, nice_ticks(min(neg), max(pos)))
    slot = p.w / n
    for i in range(n):
        up, down = 0.0, 0.0
        for k, s in enumerate(streams):
            v = s["monthly"][i]
            if not v:
                continue
            base = up if v > 0 else down
            y1, y2 = p.y(base), p.y(base + v)
            p.d.add(Rect(p.x0 + slot * i + slot * 0.15, min(y1, y2), slot * 0.7, abs(y2 - y1),
                         fillColor=SERIES[k % len(SERIES)], strokeColor=colors.white, strokeWidth=0.3))
            up, down = (up + v, down) if v > 0 else (up, down + v)
    p.month_labels(labels, slot)
    out = Drawing(width, height)
    out.add(Group(*p.d.contents))
    legend(out, [(s["name"], SERIES[k % len(SERIES)], None) for k, s in enumerate(streams)], 34, height - 10,
           width - 40)
    return out


def line_chart(labels, series, width=FRAME_W, height=58 * mm, percent=False):
    """series: [(label, values-with-None, dash or None)]. None values are gaps, never zero."""
    values = [v for _, vals, _ in series for v in vals if v is not None]
    lo, hi = (min(values), max(values)) if values else (0, 1)
    if percent:
        lo, hi = max(0.0, math.floor(lo / 10) * 10), math.ceil(hi / 10) * 10
        ticks = [lo + i * (hi - lo) / 4 for i in range(5)] if hi > lo else [lo, lo + 10]
    else:
        ticks = nice_ticks(lo, hi)
    p = Plot(width, height - 14, ticks, percent=percent)
    slot = p.w / len(labels)
    for _, vals, dash in series:
        segment = []
        for i, v in enumerate(vals + [None]):
            if v is not None:
                segment.append((p.x0 + slot * (i + 0.5), p.y(v)))
                continue
            if len(segment) > 1:
                p.d.add(PolyLine([c for pt in segment for c in pt], strokeColor=INK, strokeWidth=1.3,
                                 strokeDashArray=dash))
            for x, y in segment:
                p.d.add(Rect(x - 1.5, y - 1.5, 3, 3, fillColor=colors.white if dash else INK, strokeColor=INK,
                             strokeWidth=0.6))
            segment = []
    p.month_labels(labels, slot)
    out = Drawing(width, height)
    out.add(Group(*p.d.contents))
    legend(out, [(label, None, dash) for label, _, dash in series], 34, height - 9, width - 40)
    return out


def net_income_chart(a, width=FRAME_W, height=58 * mm):
    vals = a["net_income"]["monthly"]
    labels = a["meta"]["month_labels"]
    p = Plot(width, height - 4, nice_ticks(min(vals), max(vals)))
    slot = p.w / len(vals)
    for i, v in enumerate(vals):
        y1, y2 = p.y(0), p.y(v)
        p.d.add(Rect(p.x0 + slot * i + slot * 0.2, min(y1, y2), slot * 0.6, abs(y2 - y1),
                     fillColor=ACCENT if v >= 0 else SERIES[3], strokeColor=INK, strokeWidth=0.4))
    p.month_labels(labels, slot)
    return p.d


def opex_pairs_chart(a, width=FRAME_W):
    cats = a["operating_expenses"]["categories"]
    row_h = 15
    height = len(cats) * row_h + 34
    vals = [v for c in cats for v in (c["latest"], c["prior"])]
    ticks = nice_ticks(min(vals), max(vals))
    d = Drawing(width, height)
    x0, w = 120, width - 126
    lo, hi = ticks[0], ticks[-1]
    xv = lambda v: x0 + (v - lo) / (hi - lo) * w  # noqa: E731
    top = height - 22
    for t in ticks:
        d.add(Line(xv(t), 12, xv(t), top + 4, strokeColor=RULE, strokeWidth=0.4))
        d.add(String(xv(t), 4, tick_label(t), fontName="Helvetica", fontSize=6, fillColor=MUTED, textAnchor="middle"))
    for i, c in enumerate(cats):
        y = top - (i + 1) * row_h + 4
        d.add(String(x0 - 4, y + 3, c["name"][:30], fontName="Helvetica", fontSize=6.5, fillColor=INK,
                     textAnchor="end"))
        for j, (v, fill) in enumerate(((c["latest"], ACCENT), (c["prior"], SERIES[3]))):
            x1, x2 = xv(0), xv(v)
            d.add(Rect(min(x1, x2), y + (5 if j == 0 else 0), abs(x2 - x1), 5, fillColor=fill, strokeColor=INK,
                       strokeWidth=0.3))
    d.add(Line(xv(0), 12, xv(0), top + 4, strokeColor=INK, strokeWidth=0.9))
    legend(d, [(f"Latest ({a['meta']['latest_month']})", ACCENT, None),
               (f"Prior month ({a['meta']['prior_month']})", SERIES[3], None)], x0, height - 9, w)
    return d


# --------------------------------------------------------------------------------------------- tables
def table(rows, widths, header=True, total=False, numeric_from=1):
    data = [[Paragraph(str(c), CELL) if not isinstance(c, Paragraph) else c for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SHADE), ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK)]
    if total:
        style += [("LINEABOVE", (0, -1), (-1, -1), 0.8, INK)]
    t.setStyle(TableStyle(style))
    return t


def right(text, bold=False):
    style = ParagraphStyle("r", parent=CELL, alignment=2, fontName="Helvetica-Bold" if bold else "Helvetica")
    return Paragraph(clean(text), style)


def numeric_table(header, rows, first_width, total_row=True):
    widths = [first_width] + [(FRAME_W - first_width) / (len(header) - 1)] * (len(header) - 1)
    head = [Paragraph(f"<b>{clean(header[0])}</b>", CELL)] + [right(h, bold=True) for h in header[1:]]
    body = [[Paragraph(r[0], CELL)] + [right(c) for c in r[1:]] for r in rows]
    if body and total_row:
        body[-1] = [Paragraph(f"<b>{rows[-1][0]}</b>", CELL)] + [right(c, bold=True) for c in rows[-1][1:]]
    return table([head] + body, widths, total=total_row)


# --------------------------------------------------------------------------------------------- document
def _decorate(meta, workbook):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, PAGE_H - 11 * mm, f"{meta['company']} - monthly trend analysis, {meta['latest_month']}")
        canvas.setFillColor(DRAFT_INK)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm, "DRAFT for reviewer")
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 10 * mm, f"Numbers computed deterministically from {workbook}")
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.line(MARGIN, PAGE_H - 12.5 * mm, PAGE_W - MARGIN, PAGE_H - 12.5 * mm)
        canvas.restoreState()
    return draw


def build_story(a, report_md):
    meta = a["meta"]
    workbook = PureWindowsPath(meta["source_file"]).name
    months = meta["month_labels"]
    story = []

    # 1. Cover + key figures
    story += [Spacer(1, 6 * mm), Paragraph("Monthly trend analysis", SMALL), Paragraph(clean(meta["company"]), H1),
              Paragraph(f"Latest month: <b>{clean(meta['latest_month'])}</b> &nbsp;&middot;&nbsp; "
                        f"{len(meta['months'])} months in the export ({clean(months[0])} to {clean(months[-1])})", BODY),
              Paragraph(f"Generated {clean(meta['generated_at'])} &nbsp;&middot;&nbsp; TTM window: "
                        f"{clean(meta['ttm_window']) if meta.get('ttm_available', True) and meta.get('ttm_window') else months_note(a)}",
                        SMALL), Spacer(1, 4 * mm)]
    banner = Table([[Paragraph("<b>DRAFT for reviewer.</b> Not final and not a forecast or an accounting judgment. "
                               f"Numbers computed deterministically from <b>{clean(workbook)}</b>; "
                               "the commentary (last page) was drafted by Claude and must be reviewed.",
                               ParagraphStyle("banner", parent=BODY, textColor=DRAFT_INK))]], colWidths=[FRAME_W])
    banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), DRAFT_BG), ("BOX", (0, 0), (-1, -1), 1, DRAFT_INK),
                                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story += [banner, Spacer(1, 6 * mm), Paragraph(f"Key figures, {clean(meta['latest_month'])}", H2)]
    head = ["", f"Latest ({meta['latest_month']})", f"Prior ({meta['prior_month']})", "MoM", "Same month last year",
            "YoY", "TTM"]
    widths = [40 * mm] + [(FRAME_W - 40 * mm) / 6] * 6
    rows = [[Paragraph("", CELL)] + [right(h, bold=True) for h in head[1:]]]
    rows += [[Paragraph(f"<b>{clean(r[0])}</b>", CELL)] + [right(c) for c in r[1:]] for r in key_figures(a)]
    story += [table(rows, widths),
              Paragraph("Gross margin is shown as stored levels (latest, prior month, same month last year, TTM) so no "
                        "difference is recalculated here. " + clean(a["operating_expenses"]["total"]["name"]) + " is "
                        "operating_expenses.total: it includes "
                        + (clean(" and ".join(f"'{n}'" for n in non_operating_names(a))) + ", which the export places "
                           "inside operating expenses. The draft commentary may instead cite "
                           + clean(a["operating_expenses"]["underlying"]["name"]) + " (operating_expenses.underlying)."
                           if non_operating_names(a) else "no non-operating items in this export."), SMALL)]

    # 2. Charts (each kept together with its heading and caption; they flow across pages)
    story += [KeepTogether([Paragraph("Revenue by stream, monthly", H2), stacked_revenue_chart(a),
              Paragraph("Stacked bars; a negative month for a stream is drawn below zero. Source: revenue.streams[].monthly.",
                        SMALL)])]
    gm = a["gross_margin"]
    gm_series = [("Gross margin % (month)", [m["gm_pct"] for m in gm["monthly"]], None)]
    if meta.get("ttm_available", True) and gm.get("ttm_monthly") and any(v is not None for v in gm["ttm_monthly"]):
        gm_series.append(("TTM gross margin %", list(gm["ttm_monthly"]), (3, 2)))
        gm_note = "Source: gross_margin.monthly[].gm_pct and gross_margin.ttm_monthly."
    else:
        gm_note = f"TTM gross margin: {months_note(a)}. Source: gross_margin.monthly[].gm_pct."
    story += [KeepTogether([Paragraph("Gross margin %", H2), line_chart(months, gm_series, percent=True),
                            Paragraph(gm_note, SMALL)]),
              KeepTogether([Paragraph("Operating expenses by category: latest vs prior month", H2), opex_pairs_chart(a),
                            Paragraph("Source: operating_expenses.categories[].latest / .prior.", SMALL)]),
              KeepTogether([Paragraph("Net income, monthly", H2), net_income_chart(a),
                            Paragraph("Bars below the zero line are losses. Source: net_income.monthly.", SMALL)])]
    cash = (a.get("balance_sheet") or {}).get("lines", {}).get("cash")
    if cash and any(v is not None for v in cash.get("monthly", [])):
        label_of = dict(zip(meta["months"], months))            # 'YYYY-MM' -> 'Jan 2026', from the JSON itself
        bs_labels = [label_of.get(m, m) for m in a["balance_sheet"].get("months") or meta["months"]]
        story += [KeepTogether([Paragraph(f"Cash balance ({clean(cash['name'])})", H2),
                  line_chart(bs_labels, [("Cash balance", list(cash["monthly"]), None)], height=52 * mm),
                  Paragraph("Source: balance_sheet.lines.cash.monthly.", SMALL)])]
    else:
        story += [Paragraph("Cash balance: not available (no balance-sheet cash line in this export).", SMALL)]

    # 4. Tables
    yoy_ttm_note = ("" if meta.get("ttm_available", True)
                    else f" YoY and TTM: {months_note(a)}, shown as n/a.")
    story += [PageBreak(), Paragraph("Revenue streams", H2),
              numeric_table(["Stream", f"Latest ({meta['latest_month']})", f"Prior ({meta['prior_month']})", "MoM",
                             "YoY", "TTM"], stream_rows(a), 58 * mm),
              Paragraph("'from 0' means only that the prior month was zero, not that the line is new." + yoy_ttm_note,
                        SMALL),
              Paragraph("Operating expenses by category", H2),
              numeric_table(["Category", f"Latest ({meta['latest_month']})", f"Prior ({meta['prior_month']})", "MoM",
                             "YoY", "TTM"], category_rows(a), 58 * mm),
              Paragraph("Categories come from the keyword rules in category_map.json (or a client's --config copy)."
                        + yoy_ttm_note, SMALL)]

    # 5. Flags + data quality
    flag_rows = [[Paragraph("<b>Severity</b>", CELL), Paragraph("<b>Rule</b>", CELL), Paragraph("<b>Evidence</b>", CELL)]]
    flag_rows += [[Paragraph(clean(f["severity"]), CELL), Paragraph(clean(f["kind"]), CELL),
                   Paragraph(clean(f["message"]), CELL)] for f in a["flags"]]
    story += [PageBreak(), Paragraph("Flags raised by the rules", H2),
              table(flag_rows, [15 * mm, 37 * mm, FRAME_W - 52 * mm]),
              Paragraph("Data quality", H2)]
    check_rows = [[Paragraph("<b>Check</b>", CELL), Paragraph("<b>Result</b>", CELL), Paragraph("<b>Detail</b>", CELL)]]
    check_rows += [[Paragraph(clean(c["check"]), CELL), Paragraph(f"<b>{clean(c['status'].upper())}</b>", CELL),
                    Paragraph(clean(c.get("detail", "")), CELL)] for c in a["data_quality"]["checks"]]
    story.append(table(check_rows, [62 * mm, 23 * mm, FRAME_W - 85 * mm]))
    mism = mismatch_rows(a)
    if mism:
        story += [Paragraph("Reconciliation differences (stated subtotal vs calculated from detail rows)", H3),
                  numeric_table(["Subtotal", "Month", "Stated", "Calculated", "Difference"],
                                mism, 60 * mm, total_row=False)]
    others = [w for w in a["data_quality"]["warnings"] if w.get("type") != "subtotal_mismatch"]
    if others:
        story += [Paragraph("Other data-quality warnings", H3)] + [
            Paragraph(f"&bull; <b>{clean(w.get('type', ''))}</b>: {clean(w.get('detail', ''))}", BODY) for w in others]
    fb = a["operating_expenses"].get("fallback_accounts") or []
    story += [Paragraph(f"Accounts in '{clean(a['operating_expenses'].get('fallback_category', 'Other'))}' "
                        "(no category rule matched)", H3),
              Paragraph(clean(", ".join(fb)) if fb else "None.", BODY),
              Paragraph("Limitations", H3),
              Paragraph("This report does not cover: " + clean("; ".join(a.get("not_done", []))) + ".", BODY)]

    # 6. Commentary + checklist
    commentary = report_section(report_md, "## 1. Commentary (draft)", "### Flags raised")
    story += [PageBreak(), Paragraph("DRAFT commentary for reviewer", H2)]
    if commentary and NARRATIVE_MARKER not in commentary:
        story.append(Paragraph("Drafted by Claude from the figures above and copied verbatim from the report's "
                               "section 1. Not reviewed; every figure must be checked against the tables.", SMALL))
        for line in commentary.splitlines():
            line = line.strip()
            if line.startswith("- "):
                story.append(Paragraph(f"&bull;&nbsp;{md_inline(line[2:])}", BULLET))
            elif line:
                story.append(Paragraph(md_inline(line), BODY))
    else:
        story.append(Paragraph("No commentary has been written for this report yet (numbers-only run).", BODY))
    checklist = report_section(report_md, "## 10. For the reviewer")
    story.append(Paragraph("Reviewer checklist", H3))
    if checklist:
        for line in checklist.splitlines():
            line = line.strip()
            if line.startswith("- [ ]"):
                story.append(Paragraph(f"[&nbsp;&nbsp;] {md_inline(line[5:].strip())}", BULLET))
            elif line:
                story.append(Paragraph(md_inline(line), BODY))
    else:
        story.append(Paragraph("Not available: the report's reviewer section was not found.", BODY))
    return story


def render_pdf(analysis, report_md, out_path):
    """Write the PDF for one analysis dict. Byte-reproducible for the same inputs."""
    rl_config.invariant = 1
    meta = analysis["meta"]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=16 * mm,
                            bottomMargin=16 * mm, invariant=1, title=f"{meta['company']} - monthly trend analysis, "
                            f"{meta['latest_month']} (DRAFT)", author="monthly-trend-analysis skill",
                            creator="monthly-trend-analysis skill", subject="DRAFT for reviewer")
    decorate = _decorate(meta, PureWindowsPath(meta["source_file"]).name)
    doc.build(build_story(analysis, report_md), onFirstPage=decorate, onLaterPages=decorate)
    return out_path
