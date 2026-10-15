# Questions & answers log

Questions asked during the demo and the answers given, newest first. Each entry records when it was answered,
the data source, the answer as given, and the figures it cites. Entries are appended by the `/log-answer` command
and checked before writing: no tokens, secrets or realm IDs, and every key figure must appear in the answer.

<!-- entries: newest first. Append with /log-answer (scripts/log_answer.py); do not edit by hand. -->

## 2026-10-15 11:55 UTC · Execute the existing monthly-trend-analysis skill using the ABC Inc Excel workbook in d…

**Answered:** 2026-10-15 11:55 UTC

**Question:** Execute the existing monthly-trend-analysis skill using the ABC Inc Excel workbook in data/. Follow SKILL.md and retrieve the financial data from the workbook using the existing Python engine. Generate a report covering revenue, gross margins, operating expenses by category, month-over-month changes, trailing-twelve-month trends, and reviewer commentary. Save outputs in demo-output/ without overwriting existing committed examples. Do not modify the skill or existing code. Run the skill tests and report the results.

**Data source:** ABC workbook via the skill

**Answer:**

> The report is generated and the skill's test suite passes (44 tests, OK). The output is in a new folder, `demo-output/abc-inc-trends-run/`, so the committed `demo-output/abc-inc-2026-06-trends.*` examples are untouched.
>
> **Files**
> - `E:\RE-Finance\qbo-claude-exercise\demo-output\abc-inc-trends-run\abc-inc-2026-06-trends.md`: draft report with commentary written into section 1
> - `E:\RE-Finance\qbo-claude-exercise\demo-output\abc-inc-trends-run\abc-inc-2026-06-trends.json`: full analysis, the source for every figure
> - `E:\RE-Finance\qbo-claude-exercise\demo-output\abc-inc-trends-run\abc-inc-2026-06-trends.pdf`: rendered from the `.md`
>
> **Data quality:** all checks pass with 0 mismatches. Subtotals match their detail rows, and gross profit, operating income, net income and the balance sheet all reconcile. Jun 2026 is not flagged as partial. The export covers 18 months (Jan 2025 to Jun 2026), so TTM and year-over-year figures are available.
>
> **Key points from the commentary**
> - **Revenue:** Jun 2026 was 195,898, down 6.0% from May (208,351, the export's peak). It is -0.5% against the prior 6-month average and +2.8% against Jun 2025.
> - **Gross margin:** 70.2% in Jun 2026, up 3.1 pp from May but down 4.2 pp from Jun 2025. TTM is 69.5%.
> - **Opex:** 468,318 excluding non-operating items, down 2.4% from May. Finance & Admin moved to a (993) credit, and Travel & Entertainment rose 327%.
> - **Net income:** negative for 6 consecutive months, at (330,756) in Jun 2026 and (3,089,780) TTM. Dec 2025 is positive only because of non-operating items.
> - **Cash:** 713,481 at Jun 2026, down 215,543 from May.
> - **Zeroed lines:** Partnership Income, Professional Services and SKU Profiling are zero in recent months, and several expense lines are zero. The commentary states what the numbers show and leaves whether each has stopped or is timing to the reviewer.
>
> **Other**
> - The skill and existing code were not modified.
> - One expense account, General Expenses, matched no category rule and sits in Other Opex.
> - The commentary is my draft and needs the reviewer's sign-off before the DRAFT banner is removed.
> - The test output printed a path to the committed `demo-output/bluebird-bakery-co-2026-09-trends.pdf`. That file's timestamp and git status show it was not changed.
> - `submission/Q&A log.md` was already modified before this session started. I did not touch it.

**Key figures cited:**

- 195,898
- 208,351
- 6.0%
- -0.5%
- +2.8%
- 70.2%
- 468,318
- (330,756)
- (3,089,780)
- 713,481
- 215,543
- 44

## 2026-10-15 11:50 UTC · Using the QuickBooks MCP tools, retrieve the Profit and Loss report for the latest two…

**Answered:** 2026-10-15 11:50 UTC

**Question:** Using the QuickBooks MCP tools, retrieve the Profit and Loss report for the latest two complete months. Compare total income between the months, calculate the percentage change, and show the actual figures used. If the data is unavailable, say so instead of guessing.

**Data source:** QuickBooks sandbox via MCP

**Answer:**

> **Total income, Aug 2026 vs. Sep 2026 (QuickBooks sandbox, Accrual basis)**
>
> | Month | Total Income |
> |---|---|
> | Aug 2026 | $1,510.64 |
> | Sep 2026 | $6,915.88 |
> | Change | +$5,405.24 |
>
> **Percentage change:** (6,915.88 âˆ’ 1,510.64) Ã· 1,510.64 = **+357.8%**
>
> Sep income was about 4.6 times August's. August is a low base, so the percentage looks large. The dollar change is the more useful figure here.
>
> **Income lines behind the totals**
>
> | Income line | Aug 2026 | Sep 2026 |
> |---|---|---|
> | Landscaping Services (total) | 635.64 | 4,244.08 |
> | Design income | 975.00 | 1,275.00 |
> | Sales of Product Income | â€” | 912.75 |
> | Services | â€” | 503.55 |
> | Discounts given | â€” | âˆ’89.50 |
> | Pest Control Services | âˆ’100.00 | 70.00 |
> | **Total Income** | **1,510.64** | **6,915.88** |
>
> Landscaping Services is the largest driver: its subtotal rose by 3,608.44. That subtotal includes Job Materials and Labor.
>
> **Notes**
> - I used the Accrual method and a monthly column layout for Aug 1â€“31 and Sep 1â€“30, 2026. The request didn't specify a method. Cash-basis figures could differ.
> - The report returned complete data for both months, so nothing is missing.
> - This is sandbox data. I didn't change anything in QuickBooks.

**Key figures cited:**

- 1,510.64
- 6,915.88
- +$5,405.24
- +357.8%
- 635.64
- 4,244.08
- 3,608.44

## 2026-10-15 11:46 UTC · Retrieve the latest month's Profit and Loss report from QuickBooks and tell me the tota…

**Answered:** 2026-10-15 11:46 UTC

**Question:** Retrieve the latest month's Profit and Loss report from QuickBooks and tell me the total income.

**Data source:** QuickBooks sandbox via MCP

**Answer:**

> Total income for September 2026 was **$6,915.88** (accrual basis, sandbox QuickBooks).
>
> I used September because today is October 15, so October is still open and September is the latest complete month. The report is for September 1 to 30, 2026, with the columns summarized as a single total.

**Key figures cited:**

- $6,915.88

## 2026-10-15 11:38 UTC · What is the company name in QuickBooks? Use the QuickBooks MCP tool to verify it.

**Answered:** 2026-10-15 11:38 UTC

**Question:** What is the company name in QuickBooks? Use the QuickBooks MCP tool to verify it.

**Data source:** QuickBooks sandbox via MCP

**Answer:**

> I checked again with the QuickBooks MCP tool (`get_company_info`), and it confirms the company name is **Sandbox Company US 1bad**. The legal name is the same.

**Key figures cited:**

- Sandbox Company US 1bad

## 2026-10-15 11:36 UTC · What is the company name in QuickBooks?

**Answered:** 2026-10-15 11:36 UTC

**Question:** What is the company name in QuickBooks?

**Data source:** QuickBooks sandbox via MCP

**Answer:**

> The company name in the connected QuickBooks sandbox is **Sandbox Company US 1bad**. The legal name is the same.

**Key figures cited:**

- Sandbox Company US 1bad

## 2026-10-13 17:35 UTC · Using the ABC workbook, what was total revenue in June 2026?

**Answered:** 2026-10-13 17:35 UTC

**Question:** Using the ABC workbook, what was total revenue in June 2026?

**Data source:** ABC workbook via the skill

**Answer:**

> Total revenue for June 2026 was **195,898** in the ABC workbook. That is down 6.0% from May 2026 (208,351), up 2.8% from June 2025 (190,556), and 0.5% below the prior six-month average (196,946).
>
> The data-quality checks all passed, so the subtotal is consistent with its detail rows. The figure comes from the skill's script; the full draft report is at `trend-reports/abc-inc-2026-06-trends.md`.

**Key figures cited:**

- 195,898
- 6.0%
- 208,351
- 2.8%
- 190,556
- 0.5%
- 196,946
