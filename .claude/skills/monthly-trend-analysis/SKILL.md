---
name: monthly-trend-analysis
description: Produce a monthly trend analysis from a QuickBooks Online-style Excel export (Income Statement / Profit & Loss, optionally Balance Sheet, with one column per month). It gives revenue by stream with month-over-month %, gross margin trend, operating expenses by category, trailing-twelve-month (TTM) views, data-quality cross-checks, and draft commentary for a human reviewer to finish. Use it whenever someone asks for monthly trends, MoM or TTM figures, a month-end or management-report review, margin compression, expense movers, or "what changed this month" from a financial-statements workbook, for any company's export, even if they don't say "trend analysis". Do not use it for forecasting or budgeting, or for editing the workbook itself.
---

# Monthly trend analysis

This skill turns a monthly P&L export into a **draft** monthly trend report that a human reviewer
finishes. The numbers come from a deterministic script; your job is to run it, check its
data-quality results, and write short, factual commentary from the flags it raises.

The split matters. Financial figures must be reproducible and traceable to the workbook, so the code
computes every number. The commentary is where judgment about *what to highlight* helps the reader,
and it must never introduce a number the script didn't produce.

## Inputs

- **Workbook path** (optional). Use the path the user gives. If none is given, the script picks the
  single `.xlsx` in the repo's `data/` folder. Another company's export needs no edits to this skill:
  pass its path.
- Optional flags:
  - `--company "Name"` overrides the name read from the title rows.
  - `--months N` sets how many months appear as columns in the wide tables (default 6).
  - `--config FILE` uses a company-specific category map.
  - `--out-dir DIR` sets the output folder (default `./trend-reports`).

## Step 1: Run the analysis

Use the skill's own Python environment (it has `openpyxl`):

```bash
# Windows
.claude/skills/monthly-trend-analysis/.venv/Scripts/python .claude/skills/monthly-trend-analysis/scripts/run_trends.py "<workbook.xlsx>"
# macOS/Linux
.claude/skills/monthly-trend-analysis/.venv/bin/python .claude/skills/monthly-trend-analysis/scripts/run_trends.py "<workbook.xlsx>"
```

If `.venv` doesn't exist, create it once:
`python -m venv .claude/skills/monthly-trend-analysis/.venv`, then use that environment's Python to run
`pip install -r .claude/skills/monthly-trend-analysis/requirements.txt`. If the script is run without
`openpyxl` it prints these same instructions.

The script writes two files and prints their paths:
- `<company>-<YYYY-MM>-trends.json`: the full analysis. This is the source of truth for every number.
- `<company>-<YYYY-MM>-trends.md`: the draft report. Its sections are: commentary slot, flags, revenue
  by stream, gross margin, opex by category, movers, net income, balance sheet, data quality, account
  mapping, and a reviewer checklist.

Exit code 1 means a bad path or missing dependency. Exit code 2 means the workbook couldn't be parsed:
show the user the message, and see `references/extraction-rules.md`.

## Step 2: Check data quality before writing anything

Open the `.md` report and read **section 8 (Data quality)** first.

- If any check is `MISMATCH`, or a warning reads `subtotal_mismatch`, `unmatched_total` or
  `missing_total`, the commentary must open with it: which subtotal, which month, the stated figure,
  the detail sum. The analysis uses detail rows, and the reviewer decides which number is right. Don't
  pick one yourself.
- Note any `inferred_group` or `formula_in_detail` warnings. They're usually fine, but the reviewer
  should know the structure was reconstructed.
- If the latest month is flagged partial, say so up front, because month-over-month comparisons will
  understate it.

## Step 3: Write the commentary

Replace the line `<!-- NARRATIVE: ... -->` in section 1 of the `.md` with **4–8 bullets** for a
business owner. Base them on the flags listed directly below it and the tables, in this rough order of
importance:

1. **Top line:** revenue this month versus last month, *and* versus the recent average and the same
   month last year (from the flag text). One comparison alone can mislead. A drop from a record month
   is not the same as a drop below normal.
2. **Margin:** gross margin direction, and any compression flag.
3. **Costs:** the biggest category or account movers, and new or vanished expense lines. A vanished-line flag
   says whether the line went to zero this month ("is zero in <month>") or has been zero since an earlier
   month ("has been zero since <month>", with its last non-zero month). Keep that distinction in the prose.
4. **Profitability:** the net income trend, and any month whose sign comes only from non-operating
   items (tax, interest).
5. **Cash:** a balance-sheet cash movement, if flagged.
6. **One-offs:** single-month spikes, worded as "appears to be a single-month item; reviewer to
   confirm", never as a conclusion.

Writing rules, and why:
- **Use only figures that appear in the report or JSON.** If you need a number that isn't there, say
  it's not available instead of computing it in your head. The reviewer has to be able to trace every
  figure.
- **Describe, don't diagnose.** "Widget Rentals fell 4.2% to 12,340" (an invented example) is fine. "Customers are churning" is
  a cause the data doesn't show, so leave causes to the reviewer, or phrase them as a question for them.
- **No forecasts:** no runway, projections or "on track to". That's out of scope (below).
- **Call a line "new" or "vanished" only when a flag says so.** In the tables, `from 0` means only that the
  *previous month* was zero. The line may recur quarterly, so check its monthly history before calling it new.
- **A zero is an observation, not a conclusion.** When an expense line or revenue stream is zero, state only
  what the numbers show, such as "zero in Jun 2026" or "has been zero since Feb 2026 (last non-zero Jan 2026,
  2,500)". Then say explicitly that whether it has stopped for good, been discontinued, or is just timing is
  for the reviewer to confirm. Headings and summary phrases count too: don't let a label like "lines that
  stopped" imply permanence the data doesn't show.
- **Say what you can't compare, and why.** If TTM or year-over-year figures can't be computed (the report shows
  `n/a`), say so explicitly, name which comparisons are missing (TTM, year-over-year, or both), and give the
  number of months in the export. For example: "TTM and year-over-year comparisons aren't available: the export
  covers only 9 months (Jan–Sep 2026)." Otherwise a reader may assume the comparison was simply skipped.
- Keep each bullet to one or two sentences, with the number first. Keep "DRAFT" in the title banner.

Then tell the user where the report is, and summarise: data-quality status, the 3–4 most important
bullets, and any accounts that fell into the "Other" category.

## How the script reads the sheet (the subtotal rule)

QBO exports interleave section headers, detail accounts and subtotal rows in one column. Summing every
row double-counts. The script classifies each row structurally:

| Row | Test |
|---|---|
| **Header** | label, no value in any month: opens a section |
| **Total** | `Total X` / `Total for X` where X is an open section: closes it; that's the stated subtotal |
| **Detail** | label with values inside a section: the only rows ever summed |
| **Summary** | label with values outside all sections (Gross Profit, Net Income): cross-check only |

When a `Total X` has no matching header, the group is inferred from the preceding rows that sum to it.
If nothing matches, the row is excluded and flagged. A "header" that never gets a Total is treated as
an all-blank account, and the rows after it stay at the parent level. Bold, indentation and column
position are
deliberately **not** used, because QBO exports apply them inconsistently. Full rules, edge cases and the
JSON contract are in `references/extraction-rules.md`; read it when something parses unexpectedly.

**Cross-checks run on every report:**
- each subtotal against its detail rows;
- gross profit, operating income and net income against the sheet's own summary rows;
- assets against liabilities plus equity;
- month continuity.

A mismatch is reported, never silently resolved.

## Adapting to another company

Account names are never hardcoded. Revenue streams and COGS lines are whatever detail rows sit under
the revenue and COGS sections. Expense *categories* come from keyword rules in
`references/category_map.json`. An account that matches no rule lands in **Other Opex** and is listed
by name, so nothing is lost and the gap is visible. To adapt to a new chart of accounts, edit or copy
that JSON (patterns, section names, thresholds) and pass it with `--config`. The code doesn't change.

## What this skill does NOT do

- **No forecasting**: no runway, burn projections, budgets or trend extrapolation.
- **No accounting judgments.** It doesn't reclassify accounts, decide whether an item is truly one-off,
  adjust accruals, or choose between conflicting subtotals. Non-operating items are *shown* separately,
  never removed from the as-exported totals.
- **No currency conversion and no causal explanations.**
- **No changes to the workbook.**

All of those belong to the human reviewer. The report's section 10 is their checklist.
