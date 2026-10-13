# Evaluation report: run v4-run-20261013

- Git HEAD `6ce42f6`; working tree changes at start: 6 path(s)
- Claude Code `2.1.296 (Claude Code)`; skill model `claude-opus-5-5`; grader model `claude-sonnet-5-5`
- Golden facts consistent with workbooks: **True**
- Started 2026-10-13T03:19:07+00:00, finished 2026-10-13T03:27:20+00:00

## Summary

**Checks: 132/132 PASS, 0 FAIL, 0 BLOCKED, 0 UNSTABLE (UNSTABLE = failed in exactly 1 of 4 samples: reported, not blocking; see REGRESSION.md). Cases: 7/7 PASS.**

Regression tests (extractor layer): **Ran 31 tests in 0.342s -> OK**

**Harness contamination:** none (no file outside evals/runs/ changed during the run)


Cost: $3.05 total = $2.78 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)).

| Case | Status | Exec | Structured | Provenance | Commentary | Turns | Cost $ |
|---|---|---|---|---|---|---:|---:|
| `a_abc_jun2026_core` | **PASS** | 6/6 | 18/18 | 1/1 | 9/9 | 12 | 0.44 |
| `b_abc_rounding_vanished_lines` | **PASS** | 6/6 | 7/7 | 1/1 | 4/4 | 8 | 0.36 |
| `c_bb_subtotal_mismatch` | **PASS** | 6/6 | 8/8 | 1/1 | 4/4 | 10 | 0.38 |
| `d_bb_blank_account` | **PASS** | 6/6 | 7/7 | 1/1 | 2/2 | 11 | 0.42 |
| `e_abc_dec2025_one_offs` | **PASS** | 6/6 | 5/5 | 1/1 | 5/5 | 9 | 0.41 |
| `f_bb_from_zero_label` | **PASS** | 6/6 | 4/4 | 1/1 | 2/2 | 10 | 0.36 |
| `g_bb_no_ttm` | **PASS** | 6/6 | 6/6 | 1/1 | 2/2 | 10 | 0.40 |

## a_abc_jun2026_core: PASS

ABC Inc, Jun 2026: core figures and commentary (normal case)

Skill run: model `claude-opus-5-5`, 12 turns, 62.6 s.

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

Number provenance (P1): **PASS**, 43 matched, 25 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| R1: States Jun 2026 total revenue and that it fell versus May 2026 by about 6%. | required | **PASS** | 1/1 | States "195,898 in Jun 2026, down 6.0% from May 2026 (208,351...)"; the reference MoM is -5.98%, so 6.0% is within the policy. |
| R2: Puts the Jun 2026 revenue drop in context with at least one of: May 2026 was the highest month in the export; Jun 2026 is only about 0.5% below the prior 6-month average; Jun 2026 is about 2.8% above Jun 2025. | required | **PASS** | 1/1 | Says May was "the highest month in the export", "0.5% below the prior 6-month average" (ref -0.532%) and "2.8% above Jun 2025" (ref 2.8036%). All are consistent with the reference facts. |
| R3: Gives the Jun 2026 gross margin (about 70.2%). | required | **PASS** | 1/1 | "Gross margin: 70.2% in Jun 2026" matches the reference 70.1516%. |
| R4: States that Jun 2026 net income is negative and that losses are persistent (a run of consecutive negative months, a negative TTM figure, or negative in most months). | required | **PASS** | 1/1 | "(330,756) in Jun 2026, the sixth consecutive negative month (TTM (3,089,780); negative in 17 of 18 months)" matches the reference net income, streak of 6, TTM and count of 17. |
| R5: Notes that cash declined: gives the Jun 2026 cash balance and a decline versus the prior month and/or six months earlier. | required | **PASS** | 1/1 | Gives "713,481 at Jun 2026, down 215,543 from May 2026 and 1,871,836 lower than six months earlier (2,585,317)". The reference differences are 215,543 and 1,871,836. |
| F1: Makes any forecast or projection (cash runway, months of cash left, expected future revenue or margin, 'on track to'). | forbidden | **PASS** | 1/1 | No forecast, runway or projection appears. The "reviewer should confirm" lines are not projections. |
| F2: Asserts as fact a cause for the revenue decline that the numbers do not show (e.g. churn, pricing, lost customers, seasonality). Framing it as a question or 'reviewer to confirm' is allowed. | forbidden | **PASS** | 1/1 | The only cause-like wording is "whether any of these have stopped or whether this is timing", framed as a reviewer confirmation. No cause is asserted as fact. |
| F3: Says Jun 2026 revenue increased versus May 2026, or that Jun 2026 net income was positive. | forbidden | **PASS** | 1/1 | The commentary says revenue was "down 6.0% from May 2026" and net income was "(330,756)". It states neither a revenue increase nor positive Jun net income. |
| F4: States a figure for any of the reference facts that falls outside the rounding policy. | forbidden | **PASS** | 1/1 | Every figure that matches a reference fact is within the policy. These are revenues, MoM -6.0% vs -5.98%, 0.5% vs -0.532%, YoY 2.8%, GM 70.2%, net income, TTM, 17 months, streak of 6, and cash. Figures without a reference fact were not checked. |

## b_abc_rounding_vanished_lines: PASS

ABC Inc, Jun 2026: expense lines that went to zero, judged under the rounding policy (generalises the Task 2 '721 -> roughly 700' instance)

Skill run: model `claude-opus-5-5`, 8 turns, 49.1 s.

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

Number provenance (P1): **PASS**, 46 matched, 24 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| R1: Mentions that some expense lines were zero in Jun 2026 after being non-zero in prior months, naming at least two of: Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees. | required | **PASS** | 1/1 | The commentary says "Federal & State Taxes ... and Marketing/Advertising: Miscellaneous ... are zero in Jun 2026", and it gives prior averages for both, so they were non-zero before. That names two of the listed lines. |
| R2: Every figure given for those lines' prior averages (individually or as a range) satisfies the rounding policy. If no such figures are given, this claim PASSES. | required | **PASS** | 1/1 | It gives "prior 6-month average 999" for Federal & State Taxes, against a true 998.5083 (about 0.05% off). It gives "average 721" for Marketing Misc, against a true 721.0033 (about 0.0005% off). Both are well inside the 5% band. |
| F1: States as fact a reason those lines went to zero (e.g. contract ended, cost cutting, vendor dropped). | forbidden | **PASS** | 1/1 | No cause is stated for the zeros. The commentary only says "Whether these are discontinued or timing is for the reviewer to confirm." |
| F2: Describes those lines as permanently discontinued or cancelled without leaving it to the reviewer. | forbidden | **PASS** | 1/1 | It does not call the lines permanently discontinued or cancelled. It explicitly leaves "discontinued or timing" to the reviewer. |

## c_bb_subtotal_mismatch: PASS

Bluebird, Sep 2026: deliberately wrong subtotal is reported, not resolved

Skill run: model `claude-opus-5-5`, 10 turns, 59.2 s.

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

Number provenance (P1): **PASS**, 44 matched, 21 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| R1: Reports the data-quality problem: names the Professional Services subtotal, the month (Mar 2026), and the amount (the 25 difference, or both the stated 2,225 and the detail sum 2,200). | required | **PASS** | 1/1 | Commentary says "'Total for Professional Services' in Mar 2026 states 2,225.00, but its detail rows sum to 2,200.00 (diff 25.00)", which matches the reference facts (2,225, 2,200, 25). |
| R2: Leaves resolving the mismatch to the reviewer rather than deciding which figure is right. | required | **PASS** | 1/1 | "The reviewer should decide which figure is right." This leaves the resolution to the reviewer. The note that the report uses the detail rows is a handling choice, not a ruling on which figure is correct. |
| F1: Says all data-quality checks passed or that the data is clean/reconciled. | forbidden | **PASS** | 1/1 | The commentary flags the mismatch under "Data quality, check first" and never says the checks passed or that the data is clean or reconciled. |
| F2: Asserts which of the two figures is correct, or that the error was corrected. | forbidden | **PASS** | 1/1 | It says "This report uses the detail rows" but also "The reviewer should decide which figure is right." It does not claim either figure is correct or that the error was corrected. |

## d_bb_blank_account: PASS

Bluebird: an account blank in every month is zero and does not swallow the rows after it

Skill run: model `claude-opus-5-5`, 11 turns, 64.2 s.

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

Number provenance (P1): **PASS**, 44 matched, 23 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| F1: Describes 'Charitable Donations' as having spend/activity, or as a group or category containing other accounts. | forbidden | **PASS** | 1/1 | The commentary says 'Charitable Donations' has "no values in any of the 9 months and no total row" and was "treated as an all-blank account (0)". The 4 rows after it "were kept at the parent level", so it is not described as having spend or as a group containing accounts. |
| F2: Says Instagram Ads or Mystery Shopper Program belong to a 'Charitable Donations' or 'Finance & Admin' category. | forbidden | **PASS** | 1/1 | Mystery Shopper Program is mentioned only as an opex item (400, quarterly) with no category given. Instagram Ads is not mentioned. Neither is placed under 'Charitable Donations' or 'Finance & Admin'. |

## e_abc_dec2025_one_offs: PASS

ABC Inc: Dec 2025 stock-based compensation and bonus spikes are flagged as possible one-offs for the reviewer

Skill run: model `claude-opus-5-5`, 9 turns, 66.9 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 spike flag: Stock-Based Compensation Expense, Dec 2025 | PASS | present: /Single-month spike: 'Stock-Based Compensation Expense' .* is 334,661 in Dec 2025… | Single-month spike: 'Stock-Based Compensation Expense' (Payroll & Benefits) is 334,661 in … | literal |
| S2 spike flag: Bonus, Dec 2025 | PASS | present: /Single-month spike: 'Bonus' .* is 80,343 in Dec 2025/ | Single-month spike: 'Bonus' (Payroll & Benefits) is 80,343 in Dec 2025 | literal |
| S3 Dec 2025 SBC value | PASS | 334660.53 | 334660.53 | Income Statement!I99 |
| S4 Dec 2025 Bonus value | PASS | 80342.53 | 80342.53 | Income Statement!I33 |
| S5 Dec 2025 is the only positive net-income month | PASS | ["Dec 2025"] | ["Dec 2025"] | literal |

Number provenance (P1): **PASS**, 47 matched, 25 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| R1: Flags the Dec 2025 Stock-Based Compensation Expense spike (about 334,661) as a possible one-off / single-month item. | required | **PASS** | 1/1 | Commentary says "Stock-Based Compensation Expense 334,661 (typical month 0)... each appear to be a single-month item"; matches the reference 334,660.53. |
| R2: Flags the Dec 2025 Bonus spike (about 80,343) as a possible one-off / single-month item. | required | **PASS** | 1/1 | Commentary says "Bonus 80,343 (typical 2,721)... appear to be a single-month item"; matches the reference 80,342.53 and the median 2,720.83. |
| R3: Leaves the one-off determination to the reviewer (hedged wording such as 'appears to be' or 'reviewer to confirm') rather than concluding. | required | **PASS** | 1/1 | Uses hedged wording "each appear to be a single-month item; reviewer to confirm", so the determination is left to the reviewer. |
| F1: States as unhedged fact that these Dec 2025 items are non-recurring/one-off. | forbidden | **PASS** | 1/1 | The one-off claim is hedged ("appear to be... reviewer to confirm"), not stated as unhedged fact. |
| F2: Asserts an accounting treatment or a cause for these items as fact (e.g. 'year-end bonus accrual', 'option vesting', 'should be excluded/normalised'). | forbidden | **PASS** | 1/1 | The commentary gives no accounting treatment or cause for these items. It only notes they fall inside the TTM window, which is a factual statement, not an assertion about treatment or exclusion. |

## f_bb_from_zero_label: PASS

Bluebird, Sep 2026: prior-month-zero account labelled 'from 0', not 'new'; genuinely new stream still called new

Skill run: model `claude-opus-5-5`, 10 turns, 52.3 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 movers table labels Mystery Shopper Program 'from 0' | PASS | present: /\| Mystery Shopper Program \| Other Opex \| 0 \| 400 \| 400 \| from 0 \|/ | | Mystery Shopper Program | Other Opex | 0 | 400 | 400 | from 0 | | literal |
| S2 no 'new expense line' flag for Mystery Shopper Program | PASS | absent: /New expense line 'Mystery Shopper Program'/ | null | literal |
| S3 new-stream flag for Wholesale Accounts | PASS | present: /New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026/ | New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026 | literal |
| S4 Wholesale Accounts Sep 2026 | PASS | 12000.0 | 12000.0 | Profit and Loss!J10 |

Number provenance (P1): **PASS**, 40 matched, 18 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| R1: Identifies Wholesale Accounts as a new revenue stream in Sep 2026 (about 12,000; zero or absent in prior months). | required | **PASS** | 1/1 | Commentary says "'Wholesale Accounts' is flagged as a new stream: 12,000 in Sep 2026 and zero in the prior 6 months," matching the reference value of 12,000 and blank Jan–Aug. |
| F1: Describes Mystery Shopper Program as new, first appearing, or appearing for the first time in Sep 2026. (It was also 400 in Mar and Jun 2026. Saying it was zero in Aug, or rose 'from 0', is allowed.) | forbidden | **PASS** | 1/1 | Commentary says Mystery Shopper Program "shows as 'from 0'... but it isn't new: it also recorded 400 in Mar 2026 and Jun 2026," so it does not describe the item as new in Sep. |

## g_bb_no_ttm: PASS

Bluebird: only 9 months, so TTM / YoY are stated as unavailable, never guessed

Skill run: model `claude-opus-5-5`, 10 turns, 59.5 s.

Execution: all PASS

| Structured | Status | Expected | Actual | Source |
|---|---|---|---|---|
| S1 9 months extracted (trailing Total column ignored) | PASS | 9 | 9 | Profit and Loss!B4:J4 |
| S2 ttm_available is false | PASS | false | false | literal |
| S3 TTM revenue is null | PASS | null | null | literal |
| S4 YoY revenue is null | PASS | null | null | literal |
| S5 TTM gross margin is null | PASS | null | null | literal |
| S6 report states TTM is not available | PASS | present: /TTM \(n/a: <12 months\)/ | TTM (n/a: <12 months) | literal |

Number provenance (P1): **PASS**, 40 matched, 17 ignored, 0 unmatched.

| Claim | Kind | Status | Pass rate | Grader evidence |
|---|---|---|---|---|
| R1: Acknowledges that twelve-month comparisons (TTM and/or year-over-year) are not available because the export covers fewer than 12 months. | required | **PASS** | 1/1 | Commentary says "TTM and year-over-year comparisons can't be computed, because the export covers only 9 months (Jan–Sep 2026)", matching the reference fact of 9 months (fewer than 12). |
| F1: States any TTM, trailing-twelve-month, annualised or year-over-year figure for Bluebird, including estimates. | forbidden | **PASS** | 1/1 | No TTM, trailing-twelve-month, annualised or YoY figure is stated; it only says these are unavailable and that same-month-last-year comparison is not available. All figures given are month-over-month or against the prior 6-month average. |

## Calibration (frozen Task 2 artifact; not in the score)

`b_abc_rounding_vanished_lines` on `trend-reports/abc-inc-2026-06-trends.md @ 6ce42f6`: **PASS**

| Claim | Status | Evidence |
|---|---|---|
| R1 (required) | PASS | The commentary says "Four expense lines are zero in Jun 2026 after averaging roughly 700–1,250 a month over the prior 6 months" and names all four lines, which meets the claim. |
| R2 (required) | PASS | The range "roughly 700–1,250" has a low end of 700 against the true minimum of 721.0033, which is 2.9% off and inside 5%. The high end of 1,250 matches Advisory Services exactly. No sign or ranking changes. |
| F1 (forbidden) | PASS | No cause is stated as fact. "the reviewer should check whether this is timing" only raises timing as something to check. |
| F2 (forbidden) | PASS | The commentary does not call the lines discontinued or cancelled. It leaves the question to the reviewer. |

## Grader negative controls (synthetic text; validates the grader, not in the score)

| Control | Rule | Expected | Grader | Agrees | Evidence |
|---|---|---|---|---|---|
| ctl_c_claims_clean | R1 | FAIL | FAIL | yes | The commentary never mentions the Professional Services subtotal, Mar 2026, or the 25 difference (2,225 vs 2,200); no data-quality problem is reported. |
| ctl_c_claims_clean | R2 | FAIL | FAIL | yes | The commentary says nothing about a mismatch, so it does not leave resolution to the reviewer. |
| ctl_c_claims_clean | F1 | FAIL | FAIL | yes | It states "All data-quality checks pass and the data is fully reconciled," which is forbidden. The reference facts show a 25 mismatch in Professional Services. |
| ctl_c_claims_clean | F2 | PASS | PASS | yes | The commentary does not say which figure is correct and does not claim any error was corrected. |
| ctl_b_bad_rounding_and_cause | R1 | PASS | PASS | yes | The commentary says "Four expense lines (Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees) were zero in Jun 2026 after averaging..." It names all four lines, and the reference facts show non-zero prior averages. |
| ctl_b_bad_rounding_and_cause | R2 | FAIL | FAIL | yes | The commentary says "roughly 500-1,250". The true averages run from 721.0 (Marketing Misc) to 1,250 (Advisory). The 500 low end is about 31% below 721, which is outside the 5% band, though the 1,250 high end is exact. |
| ctl_b_bad_rounding_and_cause | F1 | FAIL | FAIL | yes | The commentary says "This is because those vendor contracts ended in May." That states a cause as fact, and nothing in the reference facts supports it. |
| ctl_g_guessed_ttm | R1 | FAIL | FAIL | yes | The commentary never says twelve-month comparisons are unavailable or that the export covers fewer than 12 months. It mentions "annualising the nine months" but gives no acknowledgement of a limitation. |
| ctl_g_guessed_ttm | F1 | FAIL | FAIL | yes | It states "On a trailing-twelve-month basis, annualising the nine months gives roughly 850,000." That is an annualised/TTM estimate, which the rule forbids. |

