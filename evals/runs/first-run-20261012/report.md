# Evaluation report: run first-run-20261012

- Git HEAD `396f17d`; working tree changes at start: 6 path(s)
- Claude Code `2.1.296 (Claude Code)`; skill model `claude-opus-5-5`; grader model `claude-sonnet-5-5`
- Golden facts consistent with workbooks: **True**
- Started 2026-10-12T07:57:51+00:00, finished 2026-10-12T08:04:55+00:00

## Summary

**Checks: 120/121 PASS, 1 FAIL, 0 BLOCKED. Cases: 6/7 PASS.**

Regression tests (extractor layer): **Ran 28 tests in 0.234s -> OK**

| Case | Status | Exec | Structured | Commentary | Turns | Cost $ |
|---|---|---|---|---|---:|---:|
| `a_abc_jun2026_core` | **FAIL** | 5/6 | 16/16 | 9/9 | 8 | 0.34 |
| `b_abc_rounding_vanished_lines` | **PASS** | 6/6 | 5/5 | 4/4 | 9 | 0.39 |
| `c_bb_subtotal_mismatch` | **PASS** | 6/6 | 8/8 | 4/4 | 9 | 0.33 |
| `d_bb_blank_account` | **PASS** | 6/6 | 7/7 | 2/2 | 10 | 0.38 |
| `e_abc_dec2025_one_offs` | **PASS** | 6/6 | 5/5 | 5/5 | 7 | 0.34 |
| `f_bb_from_zero_label` | **PASS** | 6/6 | 4/4 | 2/2 | 8 | 0.33 |
| `g_bb_no_ttm` | **PASS** | 6/6 | 6/6 | 2/2 | 8 | 0.36 |

## a_abc_jun2026_core: FAIL

ABC Inc, Jun 2026: core figures and commentary (normal case)

Skill run: model `claude-opus-5-5`, 8 turns, 42.6 s.

Execution: X5 FAIL: nothing outside evals/runs/ was modified by the run (?? evals/README.md)

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
| R1: States Jun 2026 total revenue and that it fell versus May 2026 by about 6%. | required | **PASS** | States "195,898 in Jun 2026, -6.0% vs May 2026"; the reference MoM is -5.9768%, so this is within the policy. |
| R2: Puts the Jun 2026 revenue drop in context with at least one of: May 2026 was the highest month in the export; Jun 2026 is only about 0.5% below the prior 6-month average; Jun 2026 is about 2.8% above Jun 2025. | required | **PASS** | Says May 2026 was "the highest month in the export", "-0.5% vs the prior 6-month average" (reference -0.532%) and "+2.8% vs Jun 2025" (reference 2.8036%). |
| R3: Gives the Jun 2026 gross margin (about 70.2%). | required | **PASS** | "Gross margin: 70.2% in Jun 2026" matches the reference 70.1516%. |
| R4: States that Jun 2026 net income is negative and that losses are persistent (a run of consecutive negative months, a negative TTM figure, or negative in most months). | required | **PASS** | Net income is "(330,756) in Jun 2026, the sixth consecutive negative month; TTM (3,089,780)". This matches the reference net income, the streak of 6 and the TTM. |
| R5: Notes that cash declined: gives the Jun 2026 cash balance and a decline versus the prior month and/or six months earlier. | required | **PASS** | Cash was "713,481 at Jun 2026, down 215,543 vs May 2026 and 1,871,836 vs six months earlier (2,585,317)". The reference gives 713,481.26 (Jun), 929,024.59 (May) and 2,585,317.3 (Dec), so the declines are correct. |
| F1: Makes any forecast or projection (cash runway, months of cash left, expected future revenue or margin, 'on track to'). | forbidden | **PASS** | The commentary has no forecast, runway, or expected future figures. |
| F2: Asserts as fact a cause for the revenue decline that the numbers do not show (e.g. churn, pricing, lost customers, seasonality). Framing it as a question or 'reviewer to confirm' is allowed. | forbidden | **PASS** | It gives no asserted cause for the revenue decline. The only causal-style note is "reviewer to confirm the nature of the credit", which is framed as a question. |
| F3: Says Jun 2026 revenue increased versus May 2026, or that Jun 2026 net income was positive. | forbidden | **PASS** | It says revenue was "-6.0% vs May 2026" and net income was "(330,756)", so it claims no revenue increase and no positive Jun net income. |
| F4: States a figure for any of the reference facts that falls outside the rounding policy. | forbidden | **PASS** | Every figure that matches a reference fact is within the policy: revenue 195,898, 208,351, 195,898 vs 196,946, 190,556, cash, net income and TTM. Percentages are -6.0% (ref -5.98), -0.5% (ref -0.532), +2.8% and 70.2%. The streak of six is also correct. |

## b_abc_rounding_vanished_lines: PASS

ABC Inc, Jun 2026: expense lines that went to zero, judged under the rounding policy (generalises the Task 2 '721 -> roughly 700' instance)

Skill run: model `claude-opus-5-5`, 9 turns, 51.0 s.

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
| R1: Mentions that some expense lines were zero in Jun 2026 after being non-zero in prior months, naming at least two of: Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees. | required | **PASS** | "Four expense lines are zero in Jun 2026. Their averages over the prior 6 months were Advisory Services 1,250, Professional Fees 1,045, Federal & State Taxes 999 and Marketing/Advertising: Miscellaneous 721." This names all four lines and shows they were non-zero before. |
| R2: Every figure given for those lines' prior averages (individually or as a range) satisfies the rounding policy. If no such figures are given, this claim PASSES. | required | **PASS** | Advisory Services 1,250 matches exactly. Professional Fees 1,045 vs 1,045.46 is about 0.04% off. Federal & State Taxes 999 vs 998.51 is about 0.05% off. Marketing/Advertising: Miscellaneous 721 vs 721.00 matches. All are within 5%. |
| F1: States as fact a reason those lines went to zero (e.g. contract ended, cost cutting, vendor dropped). | forbidden | **PASS** | The commentary gives no cause for the zeros. It only says "Reviewer to confirm whether these are timing or discontinued." |
| F2: Describes those lines as permanently discontinued or cancelled without leaving it to the reviewer. | forbidden | **PASS** | "Reviewer to confirm whether these are timing or discontinued" leaves the question to the reviewer and does not state the lines are permanently discontinued. |

## c_bb_subtotal_mismatch: PASS

Bluebird, Sep 2026: deliberately wrong subtotal is reported, not resolved

Skill run: model `claude-opus-5-5`, 9 turns, 48.3 s.

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
| R1: Reports the data-quality problem: names the Professional Services subtotal, the month (Mar 2026), and the amount (the 25 difference, or both the stated 2,225 and the detail sum 2,200). | required | **PASS** | States "'Total for Professional Services' in Mar 2026 states 2,225.00, but its detail rows sum to 2,200.00 (diff 25.00)", which names the subtotal, month and amounts, matching the reference facts. |
| R2: Leaves resolving the mismatch to the reviewer rather than deciding which figure is right. | required | **PASS** | "the reviewer needs to confirm which figure is correct" leaves resolution to the reviewer. |
| F1: Says all data-quality checks passed or that the data is clean/reconciled. | forbidden | **PASS** | The commentary opens with "one subtotal mismatch". The line that gross profit and net income match summary rows is limited to those items and does not say all checks passed or that the data is clean. |
| F2: Asserts which of the two figures is correct, or that the error was corrected. | forbidden | **PASS** | It says "This report uses the detail rows" but defers to the reviewer on which figure is correct. It does not claim either figure is correct or that the error was corrected. |

## d_bb_blank_account: PASS

Bluebird: an account blank in every month is zero and does not swallow the rows after it

Skill run: model `claude-opus-5-5`, 10 turns, 58.5 s.

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
| F1: Describes 'Charitable Donations' as having spend/activity, or as a group or category containing other accounts. | forbidden | **PASS** | The commentary says 'Charitable Donations' has no values and was 'treated as a blank account (0)', and that the 4 rows after it 'were kept at the parent level, not grouped under it'. It doesn't describe the account as having spend or as a group. |
| F2: Says Instagram Ads or Mystery Shopper Program belong to a 'Charitable Donations' or 'Finance & Admin' category. | forbidden | **PASS** | Instagram Ads and Mystery Shopper Program are placed in 'Other Opex' as 'accounts that matched no category rule'. Neither 'Charitable Donations' nor 'Finance & Admin' is named as their category. |

## e_abc_dec2025_one_offs: PASS

ABC Inc: Dec 2025 stock-based compensation and bonus spikes are flagged as possible one-offs for the reviewer

Skill run: model `claude-opus-5-5`, 7 turns, 47.7 s.

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
| R1: Flags the Dec 2025 Stock-Based Compensation Expense spike (about 334,661) as a possible one-off / single-month item. | required | **PASS** | Commentary says "Stock-Based Compensation Expense (334,661, median month 0)... appear to be single-month items"; matches reference 334,660.53. |
| R2: Flags the Dec 2025 Bonus spike (about 80,343) as a possible one-off / single-month item. | required | **PASS** | Commentary says "Bonus (80,343, median month 2,721)... appear to be single-month items"; matches 80,342.53 and median 2,720.83. |
| R3: Leaves the one-off determination to the reviewer (hedged wording such as 'appears to be' or 'reviewer to confirm') rather than concluding. | required | **PASS** | Uses hedged wording "each appear to be single-month items; reviewer to confirm", leaving the determination to the reviewer. |
| F1: States as unhedged fact that these Dec 2025 items are non-recurring/one-off. | forbidden | **PASS** | The one-off claim is hedged ("appear to be... reviewer to confirm"), not stated as unhedged fact. |
| F2: Asserts an accounting treatment or a cause for these items as fact (e.g. 'year-end bonus accrual', 'option vesting', 'should be excluded/normalised'). | forbidden | **PASS** | No cause or accounting treatment is asserted for SBC or Bonus; the text only notes they fall inside the TTM window and affect TTM figures. |

## f_bb_from_zero_label: PASS

Bluebird, Sep 2026: prior-month-zero account labelled 'from 0', not 'new'; genuinely new stream still called new

Skill run: model `claude-opus-5-5`, 8 turns, 48.7 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 movers table labels Mystery Shopper Program 'from 0' | PASS | present: /\| Mystery Shopper Program \| Other Opex \| 0 \| 400 \| 400 \| from 0 \|/ | | Mystery Shopper Program | Other Opex | 0 | 400 | 400 | from 0 | | literal |
| S2 no 'new expense line' flag for Mystery Shopper Program | PASS | absent: /New expense line 'Mystery Shopper Program'/ | null | literal |
| S3 new-stream flag for Wholesale Accounts | PASS | present: /New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026/ | New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026 | literal |
| S4 Wholesale Accounts Sep 2026 | PASS | 12000.0 | 12000.0 | Profit and Loss!J10 |

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Identifies Wholesale Accounts as a new revenue stream in Sep 2026 (about 12,000; zero or absent in prior months). | required | **PASS** | Commentary says "12,000 of September revenue is from 'Wholesale Accounts', a new stream" (zero in every prior month of the export), matching Wholesale Sep 2026 = 12,000 and blank before Sep. |
| F1: Describes Mystery Shopper Program as new, first appearing, or appearing for the first time in Sep 2026. (It was also 400 in Mar and Jun 2026. Saying it was zero in Aug, or rose 'from 0', is allowed.) | forbidden | **PASS** | Commentary says Mystery Shopper "shows as 'from 0', but it's not new" and recurs quarterly (Mar, Jun, Sep). This explicitly denies it is new, and "from 0" is allowed. |

## g_bb_no_ttm: PASS

Bluebird: only 9 months, so TTM / YoY are stated as unavailable, never guessed

Skill run: model `claude-opus-5-5`, 8 turns, 54.5 s.

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
| R1: Acknowledges that twelve-month comparisons (TTM and/or year-over-year) are not available because the export covers fewer than 12 months. | required | **PASS** | States "There is no same-month-last-year or TTM comparison because the export covers only Jan–Sep 2026 (9 months)", matching the reference fact of 9 months. |
| F1: States any TTM, trailing-twelve-month, annualised or year-over-year figure for Bluebird, including estimates. | forbidden | **PASS** | The commentary gives no TTM, trailing-twelve-month, annualised or YoY figure; it only mentions that such comparisons are unavailable. The comparisons it does give are month-over-month and prior 6-month average. |

## Calibration (frozen Task 2 artifact; not in the score)

`b_abc_rounding_vanished_lines` on `trend-reports/abc-inc-2026-06-trends.md @ 396f17d`: **PASS**

| Claim | Status | Evidence |
|---|---|---|
| R1 (required) | PASS | The commentary says "Four expense lines are zero in Jun 2026 after averaging roughly 700–1,250 a month over the prior 6 months" and names all four lines (Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees). |
| R2 (required) | PASS | The range "roughly 700–1,250" fits the true averages of 721.0, 998.5, 1,045.5 and 1,250. The low end of 700 is about 2.9% below 721, and the high end of 1,250 is exact. Both are inside 5%, and the four averages all fall within the range. |
| F1 (forbidden) | PASS | No cause is stated as fact. The only mention is "the reviewer should check whether this is timing", which is a suggestion to check, not an assertion. |
| F2 (forbidden) | PASS | The commentary never says the lines are discontinued or cancelled. It says they are zero in Jun 2026 and leaves the question to the reviewer. |

## Grader negative controls (synthetic text; validates the grader, not in the score)

| Control | Rule | Expected | Grader | Agrees | Evidence |
|---|---|---|---|---|---|
| ctl_c_claims_clean | R1 | FAIL | FAIL | yes | The commentary never mentions the Professional Services subtotal, Mar 2026, or the 25 difference (2,225 vs 2,200); it says all checks pass. |
| ctl_c_claims_clean | R2 | FAIL | FAIL | yes | No mismatch is raised, so nothing is left for the reviewer to resolve; it claims the data is "fully reconciled". |
| ctl_c_claims_clean | F1 | FAIL | FAIL | yes | It says "All data-quality checks pass and the data is fully reconciled," but the reference facts show a 25 mismatch in Professional Services. |
| ctl_c_claims_clean | F2 | PASS | PASS | yes | The commentary does not assert which of the two figures is correct and does not say any error was corrected. |
| ctl_b_bad_rounding_and_cause | R1 | PASS | PASS | yes | The commentary says the four named lines "were zero in Jun 2026 after averaging roughly 500-1,250 a month over the prior six months", which names all four lines and matches the reference facts (Jun 2026 = 0, prior averages non-zero). |
| ctl_b_bad_rounding_and_cause | R2 | FAIL | FAIL | yes | The stated range "500-1,250" has a lower bound of 500, but the lowest true prior average is 721.0033 (Marketing Misc). That is about 31% off, outside the 5% band. The upper bound of 1,250 is correct. |
| ctl_b_bad_rounding_and_cause | F1 | FAIL | FAIL | yes | It says "This is because those vendor contracts ended in May". That states a cause as fact, and no reference fact supports it. |
| ctl_g_guessed_ttm | R1 | FAIL | FAIL | yes | The commentary never says twelve-month comparisons are unavailable because the export covers under 12 months; it only says "annualising the nine months gives roughly 850,000", which presents a figure instead of acknowledging the limitation. |
| ctl_g_guessed_ttm | F1 | FAIL | FAIL | yes | It states "On a trailing-twelve-month basis, annualising the nine months gives roughly 850,000", which is an annualised/TTM estimate and is forbidden. |

