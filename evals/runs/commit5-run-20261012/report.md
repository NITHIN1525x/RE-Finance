# Evaluation report: run commit5-run-20261012

- Git HEAD `7f411d4`; working tree changes at start: 7 path(s)
- Claude Code `2.1.296 (Claude Code)`; skill model `claude-opus-5-5`; grader model `claude-sonnet-5-5`
- Golden facts consistent with workbooks: **True**
- Started 2026-10-12T13:05:22+00:00, finished 2026-10-12T13:13:01+00:00

## Summary

**Checks: 131/132 PASS, 1 FAIL, 0 BLOCKED. Cases: 6/7 PASS.**

Regression tests (extractor layer): **Ran 30 tests in 0.262s -> OK**

**Harness contamination:** none (no file outside evals/runs/ changed during the run)


Cost: $2.96 total = $2.69 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)).

| Case | Status | Exec | Structured | Provenance | Commentary | Turns | Cost $ |
|---|---|---|---|---|---|---:|---:|
| `a_abc_jun2026_core` | **PASS** | 6/6 | 18/18 | 1/1 | 9/9 | 16 | 0.51 |
| `b_abc_rounding_vanished_lines` | **PASS** | 6/6 | 7/7 | 1/1 | 4/4 | 11 | 0.41 |
| `c_bb_subtotal_mismatch` | **PASS** | 6/6 | 8/8 | 1/1 | 4/4 | 8 | 0.35 |
| `d_bb_blank_account` | **PASS** | 6/6 | 7/7 | 1/1 | 2/2 | 9 | 0.35 |
| `e_abc_dec2025_one_offs` | **PASS** | 6/6 | 5/5 | 1/1 | 5/5 | 7 | 0.34 |
| `f_bb_from_zero_label` | **PASS** | 6/6 | 4/4 | 1/1 | 2/2 | 8 | 0.34 |
| `g_bb_no_ttm` | **FAIL** | 6/6 | 6/6 | 1/1 | 1/2 | 9 | 0.39 |

## a_abc_jun2026_core: PASS

ABC Inc, Jun 2026: core figures and commentary (normal case)

Skill run: model `claude-opus-5-5`, 16 turns, 68.7 s.

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
| S17 revenue-stream flag: SKU Profiling has been zero since May 2026 (last non-zero Apr 2026, 10,000) [added D-48] | PASS | present: /Revenue stream 'SKU Profiling' has been zero since May 2026 \(last non-zero: Apr… | Revenue stream 'SKU Profiling' has been zero since May 2026 (last non-zero: Apr 2026, 10,0… | Income Statement!E13 |
| S18 SKU Profiling is NOT described as 'is zero in Jun 2026' (it stopped after Apr 2026) [added D-48] | PASS | absent: /Revenue stream 'SKU Profiling' is zero in Jun 2026/ | null | Income Statement!E5 |

Number provenance (P1): **PASS**, 53 matched, 30 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: States Jun 2026 total revenue and that it fell versus May 2026 by about 6%. | required | **PASS** | States "Revenue 195,898 in Jun 2026, -6.0% vs May 2026"; the reference MoM is -5.98%, so the figure is within the policy. |
| R2: Puts the Jun 2026 revenue drop in context with at least one of: May 2026 was the highest month in the export; Jun 2026 is only about 0.5% below the prior 6-month average; Jun 2026 is about 2.8% above Jun 2025. | required | **PASS** | Gives all three: May is "the highest month in the export", "-0.5% vs the prior 6-month average", and "+2.8% vs Jun 2025". These match the reference facts (-0.532%, 2.80%, May is the max). |
| R3: Gives the Jun 2026 gross margin (about 70.2%). | required | **PASS** | "Gross margin 70.2%" matches the reference 70.1516. |
| R4: States that Jun 2026 net income is negative and that losses are persistent (a run of consecutive negative months, a negative TTM figure, or negative in most months). | required | **PASS** | "Net income (330,756) in Jun 2026, the 6th consecutive negative month; TTM (3,089,780)", and "negative in 17 of 18 months". This shows a negative Jun result and persistent losses, matching the reference facts. |
| R5: Notes that cash declined: gives the Jun 2026 cash balance and a decline versus the prior month and/or six months earlier. | required | **PASS** | "Cash and Cash Equivalents 713,481 at Jun 2026, -215,543 vs May 2026 and -1,871,836 vs six months earlier". The reference differences are 215,543 and 1,871,836. |
| F1: Makes any forecast or projection (cash runway, months of cash left, expected future revenue or margin, 'on track to'). | forbidden | **PASS** | The commentary has no forecast, runway, or expected future values. It only describes past and current figures. |
| F2: Asserts as fact a cause for the revenue decline that the numbers do not show (e.g. churn, pricing, lost customers, seasonality). Framing it as a question or 'reviewer to confirm' is allowed. | forbidden | **PASS** | No cause is asserted as fact for the revenue decline. Stream and expense zeros are framed as "for the reviewer to confirm". |
| F3: Says Jun 2026 revenue increased versus May 2026, or that Jun 2026 net income was positive. | forbidden | **PASS** | It says revenue was -6.0% vs May and net income was (330,756), the 6th consecutive negative month. It does not say revenue rose vs May or that Jun net income was positive. |
| F4: States a figure for any of the reference facts that falls outside the rounding policy. | forbidden | **PASS** | All figures that match reference facts are within the policy: revenue 195,898, May 208,351, prior-6 average 196,946, Jun 2025 190,556, -6.0% vs -5.98%, -0.5% vs -0.532%, +2.8%, 70.2%, net income 330,756, TTM 3,089,780, 17 negative months, 6-month streak, and cash 713,481 and 2,585,317. No sign or direction changes. |

## b_abc_rounding_vanished_lines: PASS

ABC Inc, Jun 2026: expense lines that went to zero, judged under the rounding policy (generalises the Task 2 '721 -> roughly 700' instance)

Skill run: model `claude-opus-5-5`, 11 turns, 53.3 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 Marketing/Advertising: Miscellaneous is 0 in Jun 2026 | PASS | 0.0 | 0.0 | Income Statement!C68 |
| S2 vanished-line flag: Advisory Services has been zero since Feb 2026 (last non-zero Jan 2026, 2,500; avg 1,250) [changed D-45] | PASS | present: /Expense line 'Advisory Services' .*has been zero since Feb 2026 \(last non-zero:… | Expense line 'Advisory Services' (Professional Fees) has been zero since Feb 2026 (last no… | Income Statement!H30 |
| S3 vanished-line flag: Federal & State Taxes (avg 999) | PASS | present: /Expense line 'Federal & State Taxes' .*zero in Jun 2026; it averaged 999 / | Expense line 'Federal & State Taxes' (Finance & Admin) is zero in Jun 2026; it averaged 99… | literal |
| S4 vanished-line flag: Marketing/Advertising: Miscellaneous (avg 721) | PASS | present: /Expense line 'Marketing/Advertising: Miscellaneous' .*zero in Jun 2026; it avera… | Expense line 'Marketing/Advertising: Miscellaneous' (Sales & Marketing) is zero in Jun 202… | literal |
| S5 vanished-line flag: Professional Fees has been zero since Apr 2026 (last non-zero Mar 2026, 3,773; avg 1,045) [changed D-45] | PASS | present: /Expense line 'Professional Fees' .*has been zero since Apr 2026 \(last non-zero:… | Expense line 'Professional Fees' (Professional Fees) has been zero since Apr 2026 (last no… | Income Statement!F85 |
| S6 Advisory Services is NOT described as 'is zero in Jun 2026' (it stopped after Jan 2026) [added D-45] | PASS | absent: /Expense line 'Advisory Services' \([^)]*\) is zero in Jun 2026/ | null | Income Statement!H5 |
| S7 Professional Fees is NOT described as 'is zero in Jun 2026' (it stopped after Mar 2026) [added D-45] | PASS | absent: /Expense line 'Professional Fees' \([^)]*\) is zero in Jun 2026/ | null | Income Statement!F5 |

Number provenance (P1): **PASS**, 47 matched, 25 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Mentions that some expense lines were zero in Jun 2026 after being non-zero in prior months, naming at least two of: Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees. | required | **PASS** | The 'Expense lines at zero' bullet names Advisory Services, Professional Fees, Federal & State Taxes and Marketing/Advertising: Miscellaneous as zero in Jun 2026. It also gives prior non-zero amounts or averages for them, so they were non-zero earlier. |
| R2: Every figure given for those lines' prior averages (individually or as a range) satisfies the rounding policy. If no such figures are given, this claim PASSES. | required | **PASS** | It gives prior 6-month averages of '999 and 721'. The true values are 998.5083 and 721.0033, which differ by about 0.05% and 0.0%, so both are within the 5% band. |
| F1: States as fact a reason those lines went to zero (e.g. contract ended, cost cutting, vendor dropped). | forbidden | **PASS** | The commentary gives no cause for the zeros. It says only 'Whether any of these has ended for good or is timing is for the reviewer to confirm.' |
| F2: Describes those lines as permanently discontinued or cancelled without leaving it to the reviewer. | forbidden | **PASS** | It does not call the lines discontinued or cancelled. It leaves 'ended for good or is timing' to the reviewer. |

## c_bb_subtotal_mismatch: PASS

Bluebird, Sep 2026: deliberately wrong subtotal is reported, not resolved

Skill run: model `claude-opus-5-5`, 8 turns, 50.0 s.

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

Number provenance (P1): **PASS**, 50 matched, 25 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Reports the data-quality problem: names the Professional Services subtotal, the month (Mar 2026), and the amount (the 25 difference, or both the stated 2,225 and the detail sum 2,200). | required | **PASS** | The commentary says "'Total for Professional Services' in Mar 2026 states 2,225.00, but its detail rows sum to 2,200.00 (diff 25.00)". That names the subtotal and the month, and it gives the stated figure, the detail sum and the difference, all matching the reference facts. |
| R2: Leaves resolving the mismatch to the reviewer rather than deciding which figure is right. | required | **PASS** | "The reviewer should confirm which figure is right." This leaves the decision to the reviewer. Using the detail rows in the report is a presentation choice, not a ruling on which figure is correct. |
| F1: Says all data-quality checks passed or that the data is clean/reconciled. | forbidden | **PASS** | The commentary opens with "Data quality first: subtotal mismatch" and never says the checks passed or that the data is clean or reconciled. |
| F2: Asserts which of the two figures is correct, or that the error was corrected. | forbidden | **PASS** | It states "This report uses the detail rows" but does not say that figure is correct, and it does not say the error was corrected. It also says the reviewer should confirm which figure is right. |

## d_bb_blank_account: PASS

Bluebird: an account blank in every month is zero and does not swallow the rows after it

Skill run: model `claude-opus-5-5`, 9 turns, 54.3 s.

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

Number provenance (P1): **PASS**, 47 matched, 23 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| F1: Describes 'Charitable Donations' as having spend/activity, or as a group or category containing other accounts. | forbidden | **PASS** | The commentary says 'Charitable Donations' is 'blank in all 9 months with no total row, so it was treated as a 0 account and the 4 rows after it were kept at the parent level'. That describes no spend and no child accounts. |
| F2: Says Instagram Ads or Mystery Shopper Program belong to a 'Charitable Donations' or 'Finance & Admin' category. | forbidden | **PASS** | Mystery Shopper Program is placed in 'Other Opex', and Instagram Ads is said to have 'matched no category rule'. Neither is tied to 'Charitable Donations' or 'Finance & Admin'. |

## e_abc_dec2025_one_offs: PASS

ABC Inc: Dec 2025 stock-based compensation and bonus spikes are flagged as possible one-offs for the reviewer

Skill run: model `claude-opus-5-5`, 7 turns, 41.8 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 spike flag: Stock-Based Compensation Expense, Dec 2025 | PASS | present: /Single-month spike: 'Stock-Based Compensation Expense' .* is 334,661 in Dec 2025… | Single-month spike: 'Stock-Based Compensation Expense' (Payroll & Benefits) is 334,661 in … | literal |
| S2 spike flag: Bonus, Dec 2025 | PASS | present: /Single-month spike: 'Bonus' .* is 80,343 in Dec 2025/ | Single-month spike: 'Bonus' (Payroll & Benefits) is 80,343 in Dec 2025 | literal |
| S3 Dec 2025 SBC value | PASS | 334660.53 | 334660.53 | Income Statement!I99 |
| S4 Dec 2025 Bonus value | PASS | 80342.53 | 80342.53 | Income Statement!I33 |
| S5 Dec 2025 is the only positive net-income month | PASS | ["Dec 2025"] | ["Dec 2025"] | literal |

Number provenance (P1): **PASS**, 47 matched, 28 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Flags the Dec 2025 Stock-Based Compensation Expense spike (about 334,661) as a possible one-off / single-month item. | required | **PASS** | Commentary says "Stock-Based Compensation Expense 334,661 ... each appear to be single-month items"; the figure matches the reference value 334,660.53. |
| R2: Flags the Dec 2025 Bonus spike (about 80,343) as a possible one-off / single-month item. | required | **PASS** | Commentary says "Bonus 80,343 (typical month 2,721) each appear to be single-month items"; the figures match the reference values 80,342.53 and 2,720.83. |
| R3: Leaves the one-off determination to the reviewer (hedged wording such as 'appears to be' or 'reviewer to confirm') rather than concluding. | required | **PASS** | Uses hedged wording: "each appear to be single-month items; reviewer to confirm", so it leaves the determination to the reviewer. |
| F1: States as unhedged fact that these Dec 2025 items are non-recurring/one-off. | forbidden | **PASS** | The one-off claim is hedged ("appear to be single-month items; reviewer to confirm"), not stated as unhedged fact. |
| F2: Asserts an accounting treatment or a cause for these items as fact (e.g. 'year-end bonus accrual', 'option vesting', 'should be excluded/normalised'). | forbidden | **PASS** | The Dec 2025 items are given no cause or accounting treatment, such as bonus accrual, vesting or normalisation. Only the one-off possibility is raised. |

## f_bb_from_zero_label: PASS

Bluebird, Sep 2026: prior-month-zero account labelled 'from 0', not 'new'; genuinely new stream still called new

Skill run: model `claude-opus-5-5`, 8 turns, 51.1 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 movers table labels Mystery Shopper Program 'from 0' | PASS | present: /\| Mystery Shopper Program \| Other Opex \| 0 \| 400 \| 400 \| from 0 \|/ | | Mystery Shopper Program | Other Opex | 0 | 400 | 400 | from 0 | | literal |
| S2 no 'new expense line' flag for Mystery Shopper Program | PASS | absent: /New expense line 'Mystery Shopper Program'/ | null | literal |
| S3 new-stream flag for Wholesale Accounts | PASS | present: /New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026/ | New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026 | literal |
| S4 Wholesale Accounts Sep 2026 | PASS | 12000.0 | 12000.0 | Profit and Loss!J10 |

Number provenance (P1): **PASS**, 46 matched, 22 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Identifies Wholesale Accounts as a new revenue stream in Sep 2026 (about 12,000; zero or absent in prior months). | required | **PASS** | Commentary says "the new 'Wholesale Accounts' stream: 12,000 in Sep 2026 and zero in every earlier month", matching reference 12,000 and blank Jan–Aug. |
| F1: Describes Mystery Shopper Program as new, first appearing, or appearing for the first time in Sep 2026. (It was also 400 in Mar and Jun 2026. Saying it was zero in Aug, or rose 'from 0', is allowed.) | forbidden | **PASS** | Commentary states the Mystery Shopper Program "is not a new line. It was 400 in Mar 2026, Jun 2026 and Sep 2026"; it does not describe it as new or first appearing. |

## g_bb_no_ttm: FAIL

Bluebird: only 9 months, so TTM / YoY are stated as unavailable, never guessed

Skill run: model `claude-opus-5-5`, 9 turns, 62.4 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 9 months extracted (trailing Total column ignored) | PASS | 9 | 9 | Profit and Loss!B4:J4 |
| S2 ttm_available is false | PASS | false | false | literal |
| S3 TTM revenue is null | PASS | null | null | literal |
| S4 YoY revenue is null | PASS | null | null | literal |
| S5 TTM gross margin is null | PASS | null | null | literal |
| S6 report states TTM is not available | PASS | present: /TTM \(n/a: <12 months\)/ | TTM (n/a: <12 months) | literal |

Number provenance (P1): **PASS**, 46 matched, 22 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Acknowledges that twelve-month comparisons (TTM and/or year-over-year) are not available because the export covers fewer than 12 months. | required | **FAIL** | The commentary says only "No same-month-last-year comparison is available, because the export starts in Jan 2026." That covers year-over-year but never mentions TTM or twelve-month comparisons. It also does not say the export covers fewer than 12 months (reference: 9 months), so the claim is only partly made. |
| F1: States any TTM, trailing-twelve-month, annualised or year-over-year figure for Bluebird, including estimates. | forbidden | **PASS** | The commentary gives no TTM, trailing-twelve-month, annualised or year-over-year figures. It explicitly says no same-month-last-year comparison is available. Its figures are month-over-month and prior 6-month average comparisons. |

## Calibration (frozen Task 2 artifact; not in the score)

`b_abc_rounding_vanished_lines` on `trend-reports/abc-inc-2026-06-trends.md @ 7f411d4`: **PASS**

| Claim | Status | Evidence |
|---|---|---|
| R1 (required) | PASS | The commentary says "Four expense lines are zero in Jun 2026 after averaging roughly 700–1,250 a month over the prior 6 months" and names all four lines. That matches the reference facts, where Jun 2026 is 0 and the prior averages are non-zero. |
| R2 (required) | PASS | The stated range "roughly 700–1,250" fits the true averages of 721.00, 998.51, 1,045.46 and 1,250. The low end of 700 is about 2.9% below 721, and the high end of 1,250 is exact. Both are within 5%, and no ranking or sign changes. |
| F1 (forbidden) | PASS | No reason is stated as fact. The text only says "the reviewer should check whether this is timing", which leaves the cause open. |
| F2 (forbidden) | PASS | The commentary does not call the lines discontinued or cancelled. It defers to the reviewer with "check whether this is timing". |

## Grader negative controls (synthetic text; validates the grader, not in the score)

| Control | Rule | Expected | Grader | Agrees | Evidence |
|---|---|---|---|---|---|
| ctl_c_claims_clean | R1 | FAIL | FAIL | yes | The commentary never mentions the Professional Services subtotal, Mar 2026, or the 25 difference (2,225 vs 2,200); it says all checks pass. |
| ctl_c_claims_clean | R2 | FAIL | FAIL | yes | No mismatch is raised, so nothing is left for the reviewer to resolve; the commentary has no such claim. |
| ctl_c_claims_clean | F1 | FAIL | FAIL | yes | It states "All data-quality checks pass and the data is fully reconciled," but the reference facts show a 25 mismatch in Professional Services for Mar 2026. |
| ctl_c_claims_clean | F2 | PASS | PASS | yes | The commentary does not assert which figure is correct or that any error was corrected. |
| ctl_b_bad_rounding_and_cause | R1 | PASS | PASS | yes | The commentary names all four lines and says they "were zero in Jun 2026 after averaging roughly 500-1,250 a month", which matches the facts: Jun 2026 is 0 and the prior averages are non-zero. |
| ctl_b_bad_rounding_and_cause | R2 | FAIL | FAIL | yes | The stated range "roughly 500-1,250" has a lower bound of 500. The lowest true average is 721.0 (Marketing Misc), so 500 is about 30.7% low, outside the 5% band. The upper bound of 1,250 is correct. |
| ctl_b_bad_rounding_and_cause | F1 | FAIL | FAIL | yes | The commentary says "This is because those vendor contracts ended in May", which states a cause as fact. The reference facts give no support for it. |
| ctl_g_guessed_ttm | R1 | FAIL | FAIL | yes | The commentary never says twelve-month comparisons are unavailable or that the export covers fewer than 12 months; it instead presents a TTM/annualised figure ("annualising the nine months gives roughly 850,000"). |
| ctl_g_guessed_ttm | F1 | FAIL | FAIL | yes | It states "On a trailing-twelve-month basis, annualising the nine months gives roughly 850,000", which is a TTM/annualised estimate for Bluebird, and that is forbidden. |

