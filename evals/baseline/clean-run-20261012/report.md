# Evaluation report: run clean-run-20261012

- Git HEAD `396f17d`; working tree changes at start: 8 path(s)
- Claude Code `2.1.296 (Claude Code)`; skill model `claude-opus-5-5`; grader model `claude-sonnet-5-5`
- Golden facts consistent with workbooks: **True**
- Started 2026-10-12T11:29:01+00:00, finished 2026-10-12T11:35:54+00:00

## Summary

**Checks: 121/121 PASS, 0 FAIL, 0 BLOCKED. Cases: 7/7 PASS.**

Regression tests (extractor layer): **Ran 28 tests in 0.526s -> OK**

**Harness contamination:** none (no file outside evals/runs/ changed during the run)


Cost: $2.74 total = $2.47 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)).

| Case | Status | Exec | Structured | Commentary | Turns | Cost $ |
|---|---|---|---|---|---:|---:|
| `a_abc_jun2026_core` | **PASS** | 6/6 | 16/16 | 9/9 | 9 | 0.36 |
| `b_abc_rounding_vanished_lines` | **PASS** | 6/6 | 5/5 | 4/4 | 9 | 0.43 |
| `c_bb_subtotal_mismatch` | **PASS** | 6/6 | 8/8 | 4/4 | 7 | 0.29 |
| `d_bb_blank_account` | **PASS** | 6/6 | 7/7 | 2/2 | 8 | 0.33 |
| `e_abc_dec2025_one_offs` | **PASS** | 6/6 | 5/5 | 5/5 | 9 | 0.35 |
| `f_bb_from_zero_label` | **PASS** | 6/6 | 4/4 | 2/2 | 10 | 0.34 |
| `g_bb_no_ttm` | **PASS** | 6/6 | 6/6 | 2/2 | 10 | 0.37 |

## a_abc_jun2026_core: PASS

ABC Inc, Jun 2026: core figures and commentary (normal case)

Skill run: model `claude-opus-5-5`, 9 turns, 43.7 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 target month | PASS | Jun 2026 | Jun 2026 | literal |
| S2 Jun 2026 total revenue | PASS | 195898.16 | 195898.16 | Income Statement!C14 |
| S3 May 2026 total revenue | PASS | 208350.96 | 208350.96 | Income Statement!D14 |
| S4 revenue MoM % | PASS | -5.976838311664121 | -5.9768 | Income Statement!C14,D14 |
| S5 revenue YoY % vs Jun 2025 | PASS | 2.803648173118986 | 2.8036 | Income Statement!C14,O14 |
| S6 TTM revenue | PASS | 2303975.51 | 2303975.51 | Income Statement!C14:N14 |
| S7 number of revenue streams | PASS | 6 | 6 | Income Statement!B8:B13 |
| S8 Usage Fees Jun 2026 | PASS | 166781.5 | 166781.5 | Income Statement!C11 |
| S9 gross margin % Jun 2026 | PASS | 70.15161347099942 | 70.1516 | Income Statement!C26,C14 |
| S10 TTM gross margin % | PASS | 69.46375528097519 | 69.4638 | Income Statement!C26:N26,C14:N14 |
| S11 total opex Jun 2026 (as exported) | PASS | 468181.79999999993 | 468181.8 | Income Statement!C103 |
| S12 net income Jun 2026 | PASS | -330756.07999999996 | -330756.08 | Income Statement!C107 |
| S13 TTM net income | PASS | -3089779.59 | -3089779.59 | Income Statement!C107:N107 |
| S14 negative net-income streak | PASS | 6 | 6 | Income Statement!C107:I107 |
| S15 cash Jun 2026 | PASS | 713481.26 | 713481.26 | Balance Sheet!D15 |
| S16 all data-quality checks pass | PASS | ["pass"] | ["pass"] | literal |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: States Jun 2026 total revenue and that it fell versus May 2026 by about 6%. | required | **PASS** | "Revenue 195,898, -6.0% vs May 2026 (208,351)" matches the reference values (195,898.16; MoM -5.98%). |
| R2: Puts the Jun 2026 revenue drop in context with at least one of: May 2026 was the highest month in the export; Jun 2026 is only about 0.5% below the prior 6-month average; Jun 2026 is about 2.8% above Jun 2025. | required | **PASS** | "May was the highest month in the export", "-0.5% vs the prior 6-month average" and "+2.8% vs Jun 2025" all match the reference facts. |
| R3: Gives the Jun 2026 gross margin (about 70.2%). | required | **PASS** | "Gross margin 70.2%" matches the reference value of 70.1516. |
| R4: States that Jun 2026 net income is negative and that losses are persistent (a run of consecutive negative months, a negative TTM figure, or negative in most months). | required | **PASS** | "Net loss of (330,756) in Jun 2026, the 6th consecutive negative month; TTM (3,089,780)" matches the reference facts and shows persistent losses. |
| R5: Notes that cash declined: gives the Jun 2026 cash balance and a decline versus the prior month and/or six months earlier. | required | **PASS** | "Cash and Cash Equivalents 713,481, down 215,543 vs May 2026 and 1,871,836 vs six months earlier (2,585,317)" is consistent with the reference cash values. |
| F1: Makes any forecast or projection (cash runway, months of cash left, expected future revenue or margin, 'on track to'). | forbidden | **PASS** | The commentary has no forecast, runway or projection language. |
| F2: Asserts as fact a cause for the revenue decline that the numbers do not show (e.g. churn, pricing, lost customers, seasonality). Framing it as a question or 'reviewer to confirm' is allowed. | forbidden | **PASS** | It gives no asserted cause for the revenue decline. It only says the drop is measured from a peak, and uncertain items are flagged "reviewer to confirm". |
| F3: Says Jun 2026 revenue increased versus May 2026, or that Jun 2026 net income was positive. | forbidden | **PASS** | It says revenue fell (-6.0%) and describes a net loss. It never says revenue rose versus May or that net income was positive in Jun 2026. |
| F4: States a figure for any of the reference facts that falls outside the rounding policy. | forbidden | **PASS** | All reference-fact figures are within the policy: revenue -6.0% vs -5.98%, -0.5% vs -0.532%, +2.8% vs 2.80%, GM 70.2% vs 70.15%, TTM, cash and the streak of 6. None change sign or direction. |

## b_abc_rounding_vanished_lines: PASS

ABC Inc, Jun 2026: expense lines that went to zero, judged under the rounding policy (generalises the Task 2 '721 -> roughly 700' instance)

Skill run: model `claude-opus-5-5`, 9 turns, 62.9 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 Marketing/Advertising: Miscellaneous is 0 in Jun 2026 | PASS | 0.0 | 0.0 | Income Statement!C68 |
| S2 vanished-line flag: Advisory Services (avg 1,250) | PASS | present: /Expense line 'Advisory Services' .*zero in Jun 2026; it averaged 1,250 / | Expense line 'Advisory Services' (Professional Fees) is zero in Jun 2026; it averaged 1,25… | literal |
| S3 vanished-line flag: Federal & State Taxes (avg 999) | PASS | present: /Expense line 'Federal & State Taxes' .*zero in Jun 2026; it averaged 999 / | Expense line 'Federal & State Taxes' (Finance & Admin) is zero in Jun 2026; it averaged 99… | literal |
| S4 vanished-line flag: Marketing/Advertising: Miscellaneous (avg 721) | PASS | present: /Expense line 'Marketing/Advertising: Miscellaneous' .*zero in Jun 2026; it avera… | Expense line 'Marketing/Advertising: Miscellaneous' (Sales & Marketing) is zero in Jun 202… | literal |
| S5 vanished-line flag: Professional Fees (avg 1,045) | PASS | present: /Expense line 'Professional Fees' .*zero in Jun 2026; it averaged 1,045 / | Expense line 'Professional Fees' (Professional Fees) is zero in Jun 2026; it averaged 1,04… | literal |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Mentions that some expense lines were zero in Jun 2026 after being non-zero in prior months, naming at least two of: Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees. | required | **PASS** | The "vanished (zero in Jun 2026)" bullet names Marketing/Advertising: Miscellaneous (1,119 in May), Federal & State Taxes (1,562 in May), Advisory Services (last 2,500 in Jan 2026) and Professional Fees (2,500 Dec 2025, 3,773 Mar 2026). That covers four lines that were non-zero earlier and zero in June. |
| R2: Every figure given for those lines' prior averages (individually or as a range) satisfies the rounding policy. If no such figures are given, this claim PASSES. | required | **PASS** | The commentary gives no prior-6-month averages for these lines. It gives only individual monthly balances, so the condition for this rule is absent and it passes. |
| F1: States as fact a reason those lines went to zero (e.g. contract ended, cost cutting, vendor dropped). | forbidden | **PASS** | The commentary gives no cause for the zeros. It only describes the balance history ("not clean June drop-offs", "0 since Feb 2026"). |
| F2: Describes those lines as permanently discontinued or cancelled without leaving it to the reviewer. | forbidden | **PASS** | The commentary never calls the lines discontinued, cancelled or permanent. It only reports the history, such as "0 since Feb 2026" and "posted in only two of 18 months". |

## c_bb_subtotal_mismatch: PASS

Bluebird, Sep 2026: deliberately wrong subtotal is reported, not resolved

Skill run: model `claude-opus-5-5`, 7 turns, 41.1 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 target month | PASS | Sep 2026 | Sep 2026 | literal |
| S2 exactly one subtotal_mismatch warning | PASS | 1 | 1 | literal |
| S3 mismatch month | PASS | 2026-03 | 2026-03 | literal |
| S4 mismatch names the Professional Services subtotal | PASS | Professional Services$ | Expenses > Professional Services | literal |
| S5 stated subtotal | PASS | 2225.0 | 2225.0 | Profit and Loss!D35 |
| S6 detail-row sum | PASS | 2200.0 | 2200.0 | Profit and Loss!D33,D34 |
| S7 difference | PASS | 25.0 | 25.0 | Profit and Loss!D35,D33,D34 |
| S8 report banner shows the mismatch | PASS | present: /Data-quality checks: \*\*1 MISMATCH/ | Data-quality checks: **1 MISMATCH | literal |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Reports the data-quality problem: names the Professional Services subtotal, the month (Mar 2026), and the amount (the 25 difference, or both the stated 2,225 and the detail sum 2,200). | required | **PASS** | "'Total for Professional Services' in Mar 2026 states 2,225 but its detail rows sum to 2,200 (diff 25)" names the subtotal, month, and amounts matching reference facts. |
| R2: Leaves resolving the mismatch to the reviewer rather than deciding which figure is right. | required | **PASS** | "reviewer to decide which figure is correct" leaves resolution to the reviewer. |
| F1: Says all data-quality checks passed or that the data is clean/reconciled. | forbidden | **PASS** | The commentary flags the mismatch; the statement that gross profit and net income agree with summary rows and the balance sheet balances does not claim all checks passed or that data is clean. |
| F2: Asserts which of the two figures is correct, or that the error was corrected. | forbidden | **PASS** | It says "This analysis uses the detail rows" (a method note) and defers which figure is correct to the reviewer; it does not assert a correct figure or claim a correction. |

## d_bb_blank_account: PASS

Bluebird: an account blank in every month is zero and does not swallow the rows after it

Skill run: model `claude-opus-5-5`, 8 turns, 46.6 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 Charitable Donations is 0 in every month | PASS | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | Profit and Loss!B29:J29 |
| S2 Charitable Donations counted as 9 blank months | PASS | 9 | 9 | Profit and Loss!B4:J4 |
| S3 Instagram Ads (row below) is not grouped under it | PASS | null | null | literal |
| S4 Mystery Shopper Program (2 rows below) is not grouped under it | PASS | null | null | literal |
| S5 Instagram Ads category is the fallback, not Finance & Admin via the blank row's name | PASS | Other Opex | Other Opex | literal |
| S6 missing_total warning names Charitable Donations | PASS | 1 | 1 | literal |
| S7 opex total equals the workbook's Total for Expenses in every month (nothing lost) | PASS | [25470.0, 25215.0, 26470.0, 25485.0, 25450.0, 26115.0, 25960.0, 26085.0, 31570.0] | [25470.0, 25215.0, 26470.0, 25485.0, 25450.0, 26115.0, 25960.0, 26085.0, 31570.0] | Profit and Loss!B37:J37 |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| F1: Describes 'Charitable Donations' as having spend/activity, or as a group or category containing other accounts. | forbidden | **PASS** | Commentary says 'Charitable Donations' has no values and was 'treated as a blank account (0)' with the 4 rows 'kept at the parent level, not grouped under it', so it describes no spend and no containing group. |
| F2: Says Instagram Ads or Mystery Shopper Program belong to a 'Charitable Donations' or 'Finance & Admin' category. | forbidden | **PASS** | Instagram Ads and Mystery Shopper Program are said to 'sit in Other Opex (1,500)', not in a 'Charitable Donations' or 'Finance & Admin' category. |

## e_abc_dec2025_one_offs: PASS

ABC Inc: Dec 2025 stock-based compensation and bonus spikes are flagged as possible one-offs for the reviewer

Skill run: model `claude-opus-5-5`, 9 turns, 43.0 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 spike flag: Stock-Based Compensation Expense, Dec 2025 | PASS | present: /Single-month spike: 'Stock-Based Compensation Expense' .* is 334,661 in Dec 2025… | Single-month spike: 'Stock-Based Compensation Expense' (Payroll & Benefits) is 334,661 in … | literal |
| S2 spike flag: Bonus, Dec 2025 | PASS | present: /Single-month spike: 'Bonus' .* is 80,343 in Dec 2025/ | Single-month spike: 'Bonus' (Payroll & Benefits) is 80,343 in Dec 2025 | literal |
| S3 Dec 2025 SBC value | PASS | 334660.53 | 334660.53 | Income Statement!I99 |
| S4 Dec 2025 Bonus value | PASS | 80342.53 | 80342.53 | Income Statement!I33 |
| S5 Dec 2025 is the only positive net-income month | PASS | ["Dec 2025"] | ["Dec 2025"] | literal |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Flags the Dec 2025 Stock-Based Compensation Expense spike (about 334,661) as a possible one-off / single-month item. | required | **PASS** | Says Dec 2025 "appears to include single-month items" and cites "Stock-Based Compensation Expense of 334,661" against a typical 0, matching the reference 334,660.53. |
| R2: Flags the Dec 2025 Bonus spike (about 80,343) as a possible one-off / single-month item. | required | **PASS** | Cites "Bonus of 80,343, against typical months of 0 and 2,721" in the same single-month-items sentence; this matches the reference 80,342.53 and median 2,720.83. |
| R3: Leaves the one-off determination to the reviewer (hedged wording such as 'appears to be' or 'reviewer to confirm') rather than concluding. | required | **PASS** | Uses hedged wording: "appears to include single-month items; reviewer to confirm." It does not reach a conclusion. |
| F1: States as unhedged fact that these Dec 2025 items are non-recurring/one-off. | forbidden | **PASS** | The one-off characterisation is hedged ("appears to include single-month items; reviewer to confirm"). It is never stated as unhedged fact. |
| F2: Asserts an accounting treatment or a cause for these items as fact (e.g. 'year-end bonus accrual', 'option vesting', 'should be excluded/normalised'). | forbidden | **PASS** | The commentary gives no cause or accounting treatment for SBC or Bonus, and no "accrual", "vesting" or "should be excluded" language. The Income Tax Benefit is described only as the reason the month was positive, and the Bad Debts credit is explicitly left for the reviewer. |

## f_bb_from_zero_label: PASS

Bluebird, Sep 2026: prior-month-zero account labelled 'from 0', not 'new'; genuinely new stream still called new

Skill run: model `claude-opus-5-5`, 10 turns, 45.1 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 movers table labels Mystery Shopper Program 'from 0' | PASS | present: /\| Mystery Shopper Program \| Other Opex \| 0 \| 400 \| 400 \| from 0 \|/ | | Mystery Shopper Program | Other Opex | 0 | 400 | 400 | from 0 | | literal |
| S2 no 'new expense line' flag for Mystery Shopper Program | PASS | absent: /New expense line 'Mystery Shopper Program'/ | null | literal |
| S3 new-stream flag for Wholesale Accounts | PASS | present: /New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026/ | New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026 | literal |
| S4 Wholesale Accounts Sep 2026 | PASS | 12000.0 | 12000.0 | Profit and Loss!J10 |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Identifies Wholesale Accounts as a new revenue stream in Sep 2026 (about 12,000; zero or absent in prior months). | required | **PASS** | Commentary says "Wholesale Accounts, 12,000, is a new revenue stream: zero in every earlier month of the export," matching the reference facts (12,000 in Sep 2026, blank before). |
| F1: Describes Mystery Shopper Program as new, first appearing, or appearing for the first time in Sep 2026. (It was also 400 in Mar and Jun 2026. Saying it was zero in Aug, or rose 'from 0', is allowed.) | forbidden | **PASS** | Commentary says "Mystery Shopper Program, 400, is not new" and notes it posted 400 in Mar and Jun 2026; the "from 0" against August is allowed, so it is not described as new. |

## g_bb_no_ttm: PASS

Bluebird: only 9 months, so TTM / YoY are stated as unavailable, never guessed

Skill run: model `claude-opus-5-5`, 10 turns, 52.2 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 9 months extracted (trailing Total column ignored) | PASS | 9 | 9 | Profit and Loss!B4:J4 |
| S2 ttm_available is false | PASS | false | false | literal |
| S3 TTM revenue is null | PASS | null | null | literal |
| S4 YoY revenue is null | PASS | null | null | literal |
| S5 TTM gross margin is null | PASS | null | null | literal |
| S6 report states TTM is not available | PASS | present: /TTM \(n/a: <12 months\)/ | TTM (n/a: <12 months) | literal |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Acknowledges that twelve-month comparisons (TTM and/or year-over-year) are not available because the export covers fewer than 12 months. | required | **PASS** | The commentary says "A same-month-last-year comparison isn't available because the export starts in Jan 2026." This acknowledges that the year-over-year comparison is unavailable because the data is too short. The "and/or" in the rule allows YoY alone, and the export covers 9 months. |
| F1: States any TTM, trailing-twelve-month, annualised or year-over-year figure for Bluebird, including estimates. | forbidden | **PASS** | The commentary gives no TTM, annualised or year-over-year figure. Its comparisons are against Aug 2026, the prior 6-month average, and six months earlier. |

## Calibration (frozen Task 2 artifact; not in the score)

`b_abc_rounding_vanished_lines` on `trend-reports/abc-inc-2026-06-trends.md @ 396f17d`: **PASS**

| Claim | Status | Evidence |
|---|---|---|
| R1 (required) | PASS | The commentary says "Four expense lines are zero in Jun 2026 after averaging roughly 700–1,250 a month over the prior 6 months" and names all four lines, which is at least two. |
| R2 (required) | PASS | The range "roughly 700–1,250" matches the true averages of 721.0, 998.5, 1,045.5 and 1,250. The low end is 700 against 721 (about 2.9% off), which is within 5%, and the high end of 1,250 is exact. |
| F1 (forbidden) | PASS | The commentary gives no cause as fact. It only says "the reviewer should check whether this is timing", which leaves the reason open. |
| F2 (forbidden) | PASS | The lines are not called discontinued or cancelled. The commentary only says they are zero in Jun 2026 and leaves the question to the reviewer. |

## Grader negative controls (synthetic text; validates the grader, not in the score)

| Control | Rule | Expected | Grader | Agrees | Evidence |
|---|---|---|---|---|---|
| ctl_c_claims_clean | R1 | FAIL | FAIL | yes | The commentary never mentions the Professional Services subtotal, Mar 2026, or the 25 difference (2,225 vs 2,200). It says the data is fully reconciled instead. |
| ctl_c_claims_clean | R2 | FAIL | FAIL | yes | The commentary raises no mismatch, so it leaves nothing for the reviewer to resolve. It says "fully reconciled". |
| ctl_c_claims_clean | F1 | FAIL | FAIL | yes | It says "All data-quality checks pass and the data is fully reconciled." That is the forbidden claim, and it contradicts the 25 difference in Professional Services for Mar 2026. |
| ctl_c_claims_clean | F2 | PASS | PASS | yes | The commentary does not say which of the two figures is correct, and does not say any error was corrected. |
| ctl_b_bad_rounding_and_cause | R1 | PASS | PASS | yes | The commentary names all four lines ("Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees") as "zero in Jun 2026 after averaging" non-zero amounts over the prior six months. |
| ctl_b_bad_rounding_and_cause | R2 | FAIL | FAIL | yes | It gives the range "roughly 500-1,250". The top matches Advisory Services (1,250), but the lowest true average is 721.0033 (Marketing Misc), and 500 is about 31% below that, outside the 5% band. |
| ctl_b_bad_rounding_and_cause | F1 | FAIL | FAIL | yes | It states "This is because those vendor contracts ended in May" as fact. The reference facts give no reason for the zeros. |
| ctl_g_guessed_ttm | R1 | FAIL | FAIL | yes | The commentary never says twelve-month comparisons are unavailable or that the export covers fewer than 12 months. It only mentions "annualising the nine months" and presents an estimate. |
| ctl_g_guessed_ttm | F1 | FAIL | FAIL | yes | It states "On a trailing-twelve-month basis, annualising the nine months gives roughly 850,000". That is an annualised/TTM estimate, which the rule forbids. |

