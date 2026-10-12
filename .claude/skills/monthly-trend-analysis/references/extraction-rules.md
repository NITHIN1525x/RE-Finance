# Extraction rules and data-quality checks

Read this when a workbook parses oddly, when a data-quality check fails, or before changing
`scripts/trends/workbook.py`.

## Contents
1. Expected layout
2. Row classification (the subtotal-detection rule)
3. Why not formatting
4. Data-quality cross-checks
5. Categorisation (commentary only)
6. Output contract (JSON fields)

## 1. Expected layout

QuickBooks Online "Profit and Loss" and "Balance Sheet" exports with one column per month:
- **Title rows** come first: report title, company name, period line.
- A **header row** has a cell reading `Account`, followed by month headers. The header can be on any row
  in the first 30.
  - Month headers can be `Jun 2026`, `30 Jun 2026`, `June 2026`, `Jun-26`, `2026-06`, real date cells,
    or QBO partial periods like `Oct 1-12, 2026` (flagged as partial).
  - Columns can be newest-first or oldest-first: they are sorted ascending.
  - A trailing `Total` column is ignored because it doesn't parse as a month.
- **Labels** are in any column to the left of the first month column, and the leftmost text cell wins.
  In the ABC Inc export, top-level sections sit in column A and accounts in column B (Income Statement),
  or A/B/C (Balance Sheet).
- **Values:** blank cells count as 0 and are counted per account (`blank_months`). Text numbers such as
  `1,234.50` and `(1,234.50)` are parsed.
- Only cached values are read (`data_only=True`); a second load detects formulas. If a file was saved by
  a tool that doesn't cache formula results, values read as blank, so open and re-save it in Excel first.

## 2. Row classification: the subtotal-detection rule

Rows are read top to bottom while a **stack of open sections** is kept.

| Kind | Test | Effect |
|---|---|---|
| HEADER | label present, **no numeric value in any month column** | opens a section (pushed on the stack) |
| TOTAL | label matches `Total X` or `Total for X` (case-insensitive), and `X` equals the name of an open section (after normalising punctuation and case) | closes that section; its values are the **stated subtotal** |
| DETAIL | label with values, inside an open section | an **account**: the only rows that are ever summed |
| SUMMARY | label with values, outside every section | a computed line (`Gross Profit`, `Operating Income`, `Net Income`), used only to cross-check |

**Fallbacks.** Each one is recorded as a warning in the report; none is applied silently.

- **`Total X` with no open `X` header:** the group is inferred from the **shortest run of the
  immediately preceding sibling detail rows whose sum equals the total in every month**. Those rows
  become an "inferred group". If no run matches, the row is excluded from detail as an *unmatched
  total*, and the parent section's cross-check will show any resulting gap.
- **A header that is never closed:** QBO always writes `Total X` for a real group, so an unclosed
  "header" is treated as an **account that is blank in every month** (value 0). Any rows that had been
  nested under it go back to its parent: they were its siblings. Without this, a blank account in the
  middle of a list would capture the rows after it, and they could then be categorised by the wrong
  "group" name. Totals are unaffected either way.
- **A DETAIL row containing formulas:** it is counted, but flagged as a possible unlabeled subtotal.
- **`Parent: Child` names** (QBO sub-accounts, e.g. `Marketing/Advertising: Ad Spend`) are ordinary
  detail rows. The parent prefix is only used as a fallback when categorising.

**Example from the ABC Inc export:**
- `S & M Payroll` (no values) opens a group, then 11 accounts follow, and `Total S & M Payroll` closes
  it with `=SUM(C48:C58)`.
- `Total Operating Expenses` is `SUM(direct accounts) + Total S & M Payroll + Total Marketing`. Summing
  every row in the block would double-count both sub-groups; summing detail rows only reproduces the
  stated total exactly.

## 3. Why not formatting

Bold, indent and column position were all checked in the ABC Inc export, and none of them is reliable:
- Indent is 0 on every row.
- `Total S & M Payroll` is bold, but `Total Income` is not.
- The Balance Sheet header `Cash and Cash Equivalents` sits in the same column as its accounts.

Formulas are a good *confirmation*: in this file every subtotal and computed row is a formula and every
detail row is a value. But exports saved as values only exist, so formulas are used only to raise
warnings. The structural rule above works with or without them.

## 4. Data-quality cross-checks

| Check | Rule | On failure |
|---|---|---|
| Subtotal vs detail | every stated subtotal = sum of the detail rows beneath it (nested groups flattened), per month, tolerance 0.01 | `subtotal_mismatch` warning with stated, detail sum and difference. **Analysis uses the detail rows**, and the report shows both numbers |
| Gross profit | revenue detail − COGS detail = the sheet's `Gross Profit` row | `mismatch` in the checks table |
| Operating income / net income | recomputed from detail (other income/expense sections included) = the sheet's rows | `mismatch` |
| Balance sheet balances | `Assets` total = `Liabilities and Equity` total, per month | `mismatch` |
| Month continuity | header months are contiguous, with no duplicates | `month_gap` / `duplicate_month` warning |
| Partial month | latest column is a partial period | high flag: MoM understates it |
| Unknown section | a top-level section matches no `statement_sections` pattern | high flag: listed but excluded from margins |

## 5. Categorisation (commentary only)

`references/category_map.json` groups expense accounts into categories. The first rule wins, and it is
tested against the account name, then its `Parent:` prefix, then enclosing sub-group headers (innermost
first). An account no rule matches goes to `fallback_category` ("Other Opex") and is listed by name in
the report.

`non_operating: true` categories (tax, interest) are shown separately, and "Operating expenses excl.
non-operating items" is reported next to the as-exported total. **Totals always reconcile to the
workbook**; categories never change a number.

Revenue streams and COGS lines are taken as they are: each detail account in a revenue or COGS section
is one line. No mapping is needed.

## 6. Output contract (`*-trends.json`)

| Key | Contents |
|---|---|
| `meta` | company, source_file, sheets, months (`YYYY-MM`), month_labels, latest/prior month, ttm_window, partial_months, materiality, generated_at |
| `revenue.total`, `revenue.streams[]` | series blocks (below) |
| `gross_margin` | `monthly[]` {month, revenue, cogs, gross_profit, gm_pct}, ttm_gm_pct, ttm_monthly, cogs_lines[] |
| `operating_expenses` | `categories[]` (blocks + non_operating + accounts), `accounts[]` (blocks + category + matched_on + group), `total`, `underlying`, fallback_accounts |
| `net_income` | block + negative_streak_months, negative_months, positive_months, underlying_monthly, underlying_ttm |
| `balance_sheet` | `lines` {cash, total_assets, liabilities, equity, liabilities_and_equity}: monthly, latest, prior, six_months_earlier |
| `movers` | top categories and accounts by absolute change, latest vs prior |
| `flags[]` | {severity: high/medium/info, kind, message, figures?}, with rule-based text only |
| `data_quality` | checks[] {check, status: pass/mismatch/skipped/partial, detail}, warnings[] |
| `not_done[]` | what the analysis deliberately does not do |

A **series block** holds: `name`, `monthly[]` (aligned with `meta.months`), `latest`, `prior`,
`mom_abs`, `mom_pct` (percent; null when the prior month is 0), `ttm`, `ttm_prior_month`,
`ttm_monthly[]` (null until 12 months exist), `same_month_last_year`, `yoy_pct`.
