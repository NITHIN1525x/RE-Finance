# Evaluation report: run caseb-before-1

- Git HEAD `7f411d4`; working tree changes at start: 6 path(s)
- Claude Code `2.1.296 (Claude Code)`; skill model `claude-opus-5-5`; grader model `claude-sonnet-5-5`
- Golden facts consistent with workbooks: **True**
- Started 2026-10-12T12:47:49+00:00, finished 2026-10-12T12:49:25+00:00

## Summary

**Checks: 18/18 PASS, 0 FAIL, 0 BLOCKED. Cases: 1/1 PASS.**

Regression tests (extractor layer): **Ran 30 tests in 0.295s -> OK**

**Harness contamination:** none (no file outside evals/runs/ changed during the run)


Cost: $0.60 total = $0.49 for 1 skill runs + $0.12 for 5 grader calls (total_cost_usd reported by Claude Code for each call (list prices)).

| Case | Status | Exec | Structured | Provenance | Commentary | Turns | Cost $ |
|---|---|---|---|---|---|---:|---:|
| `b_abc_rounding_vanished_lines` | **PASS** | 6/6 | 7/7 | 1/1 | 4/4 | 14 | 0.49 |

## b_abc_rounding_vanished_lines: PASS

ABC Inc, Jun 2026: expense lines that went to zero, judged under the rounding policy (generalises the Task 2 '721 -> roughly 700' instance)

Skill run: model `claude-opus-5-5`, 14 turns, 61.4 s.

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

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Mentions that some expense lines were zero in Jun 2026 after being non-zero in prior months, naming at least two of: Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees. | required | **PASS** | The commentary says "Federal & State Taxes and Marketing/Advertising: Miscellaneous are zero in Jun 2026", and it also names Advisory Services and Professional Fees as zero. That gives at least two named lines that were zero in Jun 2026 after being non-zero earlier. |
| R2: Every figure given for those lines' prior averages (individually or as a range) satisfies the rounding policy. If no such figures are given, this claim PASSES. | required | **PASS** | The commentary gives prior 6-month averages of "999 and 721". The true values are 998.5083 and 721.0033, which differ by about 0.05% and 0.0%, so both are within the 5% band. |
| F1: States as fact a reason those lines went to zero (e.g. contract ended, cost cutting, vendor dropped). | forbidden | **PASS** | The commentary only reports that the lines are zero or no longer appearing, with last non-zero months. It states no cause such as a contract ending or cost cutting. |
| F2: Describes those lines as permanently discontinued or cancelled without leaving it to the reviewer. | forbidden | **PASS** | The commentary says the lines are "zero since" certain months and "no longer appearing". It does not call them permanently discontinued or cancelled. |

## Calibration (frozen Task 2 artifact; not in the score)

`b_abc_rounding_vanished_lines` on `trend-reports/abc-inc-2026-06-trends.md @ 7f411d4`: **PASS**

| Claim | Status | Evidence |
|---|---|---|
| R1 (required) | PASS | Commentary says "Four expense lines are zero in Jun 2026 after averaging roughly 700–1,250 a month over the prior 6 months" and names all four lines, which matches the zero Jun 2026 values and non-zero prior averages. |
| R2 (required) | PASS | The range "roughly 700–1,250" matches the true averages of 721.0033 to 1,250. The low end of 700 is 2.9% below 721, and the high end is exact, so both are within 5%. |
| F1 (forbidden) | PASS | No cause is stated as fact. The only explanation is "the reviewer should check whether this is timing", which is a suggestion to check and not an assertion. |
| F2 (forbidden) | PASS | The lines are not described as permanently discontinued or cancelled. The commentary leaves the question to the reviewer with "should check whether this is timing". |

## Grader negative controls (synthetic text; validates the grader, not in the score)

| Control | Rule | Expected | Grader | Agrees | Evidence |
|---|---|---|---|---|---|
| ctl_c_claims_clean | R1 | FAIL | FAIL | yes | The commentary never mentions the Professional Services subtotal, Mar 2026, or the 25 difference (2,225 vs 2,200); the claim is absent. |
| ctl_c_claims_clean | R2 | FAIL | FAIL | yes | No mismatch is mentioned, so nothing is left to the reviewer to resolve; the commentary says only "fully reconciled". |
| ctl_c_claims_clean | F1 | FAIL | FAIL | yes | It says "All data-quality checks pass and the data is fully reconciled." That is forbidden, and it contradicts the 25 difference in the reference facts. |
| ctl_c_claims_clean | F2 | PASS | PASS | yes | The commentary does not say which of the two figures is correct or that any error was corrected. |
| ctl_b_bad_rounding_and_cause | R1 | PASS | PASS | yes | The commentary says "Four expense lines (Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees) were zero in Jun 2026 after averaging...". That names all four lines and says they were non-zero before. |
| ctl_b_bad_rounding_and_cause | R2 | FAIL | FAIL | yes | The commentary gives a range of "roughly 500-1,250". The true averages run from 721.0 (Marketing Misc) to 1,250 (Advisory). The 500 lower bound is about 31% below 721, which is outside the 5% band, so it is a misstatement. |
| ctl_b_bad_rounding_and_cause | F1 | FAIL | FAIL | yes | The commentary says "This is because those vendor contracts ended in May." That states a cause as fact. |
| ctl_g_guessed_ttm | R1 | FAIL | FAIL | yes | The commentary never says twelve-month comparisons are unavailable; it says "On a trailing-twelve-month basis, annualising the nine months gives roughly 850,000", which presents a TTM-style figure instead of acknowledging the limitation. |
| ctl_g_guessed_ttm | F1 | FAIL | FAIL | yes | It states "annualising the nine months gives roughly 850,000" on a "trailing-twelve-month basis". That is an annualised/TTM estimate, which the rule forbids. |

