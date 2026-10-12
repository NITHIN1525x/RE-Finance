"""Parse one QBO-style report sheet (Income Statement / Balance Sheet export) into a structure.

Layout assumptions (verified on the ABC Inc export, kept deliberately loose):
- A header row somewhere in the first 30 rows has a cell reading "Account" (configurable); every cell to its
  right that parses as a month is a period column. Order may be newest-first or oldest-first; we sort.
- Labels sit in any column left of the first month column (top-level sections are often one column further
  left). The label of a row is its leftmost non-empty text cell.

Row classification (the subtotal-detection rule; see references/extraction-rules.md):
  1. HEADER   label, no numeric value in any month column        -> opens a section
  2. TOTAL    label "Total X" / "Total for X" and X names an open section -> closes it; values = stated subtotal
  3. DETAIL   label with values, inside an open section            -> an account (the only rows summed)
  4. SUMMARY  label with values, outside every section             -> computed line (Gross Profit, Net Income...)
  Fallbacks (each recorded as a warning, never silent):
  - TOTAL with no matching open header: infer the group from the shortest run of preceding sibling detail
    rows whose sum equals the stated total in every month; if none matches, keep it as an unreconciled total.
  - HEADER never closed: if it got no rows it was an all-blank account (value 0); otherwise it is closed when
    its parent closes.
  - A DETAIL row whose month cells are formulas is flagged: it may be an unlabeled subtotal.
Formatting (bold/indent/column) is recorded for diagnostics but never used to decide, because the source
exports are inconsistent about it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

TOLERANCE = 0.01  # currency units; subtotal differences above this are data-quality warnings

_MONTH_FORMATS = ["%b %Y", "%B %Y", "%d %b %Y", "%d %B %Y", "%b-%y", "%b-%Y", "%Y-%m", "%m/%Y", "%b %d, %Y"]
# QBO partial periods look like "Oct 1-12, 2026": month + day range + year.
_PARTIAL_RE = re.compile(r"^([A-Za-z]{3,9})\s+\d{1,2}\s*-\s*\d{1,2},?\s+(\d{4})$")
_TOTAL_RE = re.compile(r"^\s*total(?:\s+for)?\s+(?P<name>.+?)\s*$", re.IGNORECASE)


# ----------------------------------------------------------------------------------------------- data classes
@dataclass
class Account:
    name: str
    row: int
    values: list[float]
    blank_months: int = 0          # cells that were empty and treated as 0
    has_formula: bool = False

    @property
    def parent_name(self):
        """QBO flattens sub-accounts as 'Parent: Child' (or 'Parent:Child')."""
        return self.name.split(":", 1)[0].strip() if ":" in self.name else None


@dataclass
class Section:
    name: str
    row: int | None                # header row (None for an inferred group)
    depth: int
    children: list = field(default_factory=list)        # Account | Section, in sheet order
    stated_total: list[float] | None = None
    total_row: int | None = None
    total_label: str | None = None
    inferred: bool = False         # group reconstructed from numbers (no header row)

    def accounts(self):
        """All detail accounts below this section (nested groups flattened)."""
        for child in self.children:
            if isinstance(child, Account):
                yield child, [self.name]
            else:
                for acc, path in child.accounts():
                    yield acc, [self.name, *path]

    def detail_sum(self, n):
        out = [0.0] * n
        for acc, _ in self.accounts():
            out = [a + b for a, b in zip(out, acc.values)]
        return out


@dataclass
class SummaryRow:
    name: str
    row: int
    values: list[float]


@dataclass
class Sheet:
    title: str
    title_lines: list[str]
    months: list[date]             # ascending
    partial_months: list[date]     # months whose header indicated a partial period
    sections: list[Section]        # top-level sections in order
    summaries: list[SummaryRow]
    warnings: list[dict]
    header_row: int
    label_columns: str


# ----------------------------------------------------------------------------------------------- helpers
def parse_month(value):
    """Return (first-of-month date, is_partial) or (None, False)."""
    if isinstance(value, datetime):
        return date(value.year, value.month, 1), False
    if isinstance(value, date):
        return date(value.year, value.month, 1), False
    if not isinstance(value, str):
        return None, False
    text = " ".join(value.strip().split())
    for fmt in _MONTH_FORMATS:
        try:
            d = datetime.strptime(text, fmt)
            return date(d.year, d.month, 1), False
        except ValueError:
            pass
    m = _PARTIAL_RE.match(text)
    if m:
        for fmt in ("%b %Y", "%B %Y"):
            try:
                d = datetime.strptime(f"{m.group(1)} {m.group(2)}", fmt)
                return date(d.year, d.month, 1), True
            except ValueError:
                pass
    return None, False


def parse_number(value):
    """Cell value -> float, or None if the cell is empty / not numeric. Accepts '1,234.50' and '(1,234.50)'."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace("$", "")
        if not text:
            return None
        neg = text.startswith("(") and text.endswith(")")
        text = text.strip("()")
        try:
            return -float(text) if neg else float(text)
        except ValueError:
            return None
    return None


def norm(name):
    """Normalise a label for matching 'Total X' to header 'X'."""
    return re.sub(r"[^a-z0-9&]+", " ", str(name).casefold()).strip()


def total_target(label):
    m = _TOTAL_RE.match(label or "")
    return m.group("name") if m else None


# ----------------------------------------------------------------------------------------------- header detection
def find_header(ws_values, header_label="Account", max_scan=30):
    """Locate the header row: a cell equal to header_label followed by >= 2 month columns.
    Falls back to the first row that has >= 2 parseable months if no 'Account' cell exists."""
    fallback = None
    for r in range(1, min(ws_values.max_row, max_scan) + 1):
        label_col, months = None, []
        for c in range(1, ws_values.max_column + 1):
            v = ws_values.cell(r, c).value
            if isinstance(v, str) and v.strip().casefold() == header_label.casefold():
                label_col = c
            m, partial = parse_month(v)
            if m:
                months.append((c, m, partial))
        if len(months) >= 2:
            if label_col is not None:
                return r, label_col, months
            fallback = fallback or (r, None, months)
    if fallback:
        return fallback
    raise ValueError(f"No header row with '{header_label}' and month columns found in sheet '{ws_values.title}'")


# ----------------------------------------------------------------------------------------------- main parser
def parse_sheet(ws_values, ws_formulas=None, header_label="Account"):
    """ws_values: worksheet loaded with data_only=True (cached values). ws_formulas: same sheet loaded normally
    (optional) so formula cells can be detected. Returns a Sheet."""
    header_row, label_col, month_cols = find_header(ws_values, header_label)
    first_month_col = min(c for c, _, _ in month_cols)
    label_cols = range(1, first_month_col)
    title_lines = [str(ws_values.cell(r, c).value).strip() for r in range(1, header_row) for c in label_cols
                   if isinstance(ws_values.cell(r, c).value, str) and ws_values.cell(r, c).value.strip()]

    # Sort period columns ascending (exports are often newest-first) and de-duplicate months.
    month_cols = sorted(month_cols, key=lambda t: t[1])
    warnings = []
    seen = {}
    for c, m, p in month_cols:
        if m in seen:
            warnings.append({"type": "duplicate_month", "detail": f"Month {m:%b %Y} appears in two columns; using the first"})
        seen.setdefault(m, (c, p))
    months = sorted(seen)
    cols = [seen[m][0] for m in months]
    partial = [m for m in months if seen[m][1]]
    for a, b in zip(months, months[1:]):
        if (b.year * 12 + b.month) - (a.year * 12 + a.month) != 1:
            warnings.append({"type": "month_gap", "detail": f"Months are not contiguous between {a:%b %Y} and {b:%b %Y}"})
    n = len(months)

    root = Section(name="__root__", row=None, depth=-1)
    stack = [root]
    summaries = []

    def close(section, total_values=None, total_row=None, total_label=None):
        section.stated_total = total_values
        section.total_row, section.total_label = total_row, total_label

    for r in range(header_row + 1, ws_values.max_row + 1):
        label, label_at = None, None
        for c in label_cols:
            v = ws_values.cell(r, c).value
            if isinstance(v, str) and v.strip():
                label, label_at = " ".join(v.split()), c
                break
        raw = [ws_values.cell(r, c).value for c in cols]
        nums = [parse_number(v) for v in raw]
        has_values = any(v is not None for v in nums)
        if label is None:
            if has_values:
                warnings.append({"type": "unlabeled_values", "row": r, "detail": f"Row {r} has values but no label; ignored"})
            continue
        values = [v if v is not None else 0.0 for v in nums]
        formula = False
        if ws_formulas is not None:
            formula = any(isinstance(ws_formulas.cell(r, c).value, str) and str(ws_formulas.cell(r, c).value).startswith("=")
                          for c in cols)
        target = total_target(label)

        # 2. TOTAL row
        if target is not None:
            match_idx = next((i for i in range(len(stack) - 1, 0, -1) if norm(stack[i].name) == norm(target)), None)
            if match_idx is not None:
                # Close any open sections nested inside the matched one first (they had no Total row).
                while len(stack) - 1 > match_idx:
                    inner = stack.pop()
                    _finish_unclosed(inner, stack[-1], n, warnings)
                close(stack.pop(), values, r, label)
                continue
            inferred = _infer_group(stack[-1], target, values, r, label, warnings)
            if inferred:
                continue
            # Not a subtotal we can reconcile: keep it out of the detail, flag it.
            warnings.append({"type": "unmatched_total", "row": r, "label": label,
                             "detail": f"'{label}' has no matching header and no run of rows above sums to it; "
                                       "excluded from detail (check manually)"})
            continue

        # 1. HEADER row
        if not has_values:
            parent = stack[-1]
            sec = Section(name=label, row=r, depth=len(stack) - 1)
            parent.children.append(sec)
            stack.append(sec)
            continue

        # 4. SUMMARY row (outside every section)
        if len(stack) == 1:
            summaries.append(SummaryRow(label, r, values))
            continue

        # 3. DETAIL row
        acc = Account(label, r, values, blank_months=sum(1 for v in nums if v is None), has_formula=formula)
        if formula:
            warnings.append({"type": "formula_in_detail", "row": r, "label": label,
                             "detail": f"Detail row '{label}' contains formulas: it may be an unlabeled subtotal. "
                                       "It is counted as an account; verify it is not double-counted."})
        stack[-1].children.append(acc)

    while len(stack) > 1:
        inner = stack.pop()
        _finish_unclosed(inner, stack[-1], n, warnings)

    top = [c for c in root.children if isinstance(c, Section)]
    stray = [c for c in root.children if isinstance(c, Account)]
    for acc in stray:  # cannot happen with the rules above, kept as a guard
        warnings.append({"type": "orphan_account", "label": acc.name, "detail": "Account outside any section"})

    sheet = Sheet(title=ws_values.title, title_lines=title_lines, months=months, partial_months=partial,
                  sections=top, summaries=summaries, warnings=warnings, header_row=header_row,
                  label_columns=",".join(chr(64 + c) for c in label_cols))
    cross_check_subtotals(sheet)
    return sheet


def _finish_unclosed(section, parent, n, warnings):
    """A 'header' that never got its Total row. QBO always writes 'Total X' for a real group, so an unclosed
    header is most likely an account that is blank in every month. Turn it into a zero account and give any
    rows that were nested under it back to the parent (they are its siblings). Totals are unaffected either
    way; this only prevents those rows being categorised by the wrong 'group' name."""
    idx = parent.children.index(section)
    blank = Account(section.name, section.row, [0.0] * n, blank_months=n)
    parent.children[idx:idx + 1] = [blank, *section.children]
    if section.children:
        warnings.append({"type": "missing_total", "label": section.name,
                         "detail": f"'{section.name}' has no values and no 'Total {section.name}' row; treated as an "
                                   f"all-blank account (0). The {len(section.children)} row(s) after it were kept at the "
                                   "parent level, not grouped under it."})
    else:
        warnings.append({"type": "empty_header", "label": section.name,
                         "detail": f"'{section.name}' has no values in any month; treated as an all-blank account (0)"})


def _infer_group(parent, target, values, row, label, warnings):
    """'Total X' with no 'X' header: find the shortest trailing run of the parent's direct accounts whose
    monthly sum equals the stated total, and wrap them in an inferred group."""
    trailing = []
    for child in reversed(parent.children):
        if not isinstance(child, Account):
            break
        trailing.insert(0, child)
    for size in range(1, len(trailing) + 1):
        run = trailing[-size:]
        sums = [sum(a.values[i] for a in run) for i in range(len(values))]
        if all(abs(s - v) <= TOLERANCE for s, v in zip(sums, values)):
            group = Section(name=target, row=None, depth=parent.depth + 1, children=run, inferred=True,
                            stated_total=values, total_row=row, total_label=label)
            parent.children = parent.children[: len(parent.children) - size] + [group]
            warnings.append({"type": "inferred_group", "row": row, "label": label,
                             "detail": f"'{label}' has no header row; grouped the {size} row(s) above it "
                                       f"({', '.join(a.name for a in run)}) because they sum to it in every month"})
            return True
    return False


def cross_check_subtotals(sheet):
    """Compare each stated subtotal with the sum of the detail rows beneath it (detail rows are the truth for
    category analysis; the stated number is reported alongside, never silently replaced)."""
    n = len(sheet.months)

    def walk(sec, path):
        for child in sec.children:
            if isinstance(child, Section):
                walk(child, path + [child.name])
        if sec.stated_total is not None:
            computed = sec.detail_sum(n)
            for i, (s, c) in enumerate(zip(sec.stated_total, computed)):
                if abs(s - c) > TOLERANCE:
                    sheet.warnings.append({
                        "type": "subtotal_mismatch", "section": " > ".join(path), "row": sec.total_row,
                        "month": sheet.months[i].isoformat()[:7], "stated": round(s, 2), "detail_sum": round(c, 2),
                        "difference": round(s - c, 2),
                        "detail": f"'{sec.total_label}' in {sheet.months[i]:%b %Y} states {s:,.2f} but its detail rows sum "
                                  f"to {c:,.2f} (diff {s - c:,.2f}). Analysis uses the detail rows; reviewer to confirm."})

    for top in sheet.sections:
        walk(top, [top.name])


def load_workbook_pair(path):
    """Two loads, per the xlsx skill: cached values + formulas."""
    import openpyxl
    return openpyxl.load_workbook(path, data_only=True, read_only=False), openpyxl.load_workbook(path, read_only=False)


def find_sheet(workbook, patterns):
    """First sheet whose name matches any regex in patterns (case-insensitive), else None."""
    for ws in workbook.worksheets:
        if any(re.search(p, ws.title, re.IGNORECASE) for p in patterns):
            return ws
    return None
