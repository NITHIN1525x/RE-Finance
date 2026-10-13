# Evaluation report: run caseb-after-2

- Git HEAD `7f411d4`; working tree changes at start: 7 path(s)
- Claude Code `2.1.296 (Claude Code)`; skill model `claude-opus-5-5`; grader model `claude-sonnet-5-5`
- Golden facts consistent with workbooks: **True**
- Started 2026-10-12T12:57:51+00:00, finished 2026-10-12T12:59:25+00:00

## Summary

**Checks: 18/18 PASS, 0 FAIL, 0 BLOCKED. Cases: 1/1 PASS.**

Regression tests (extractor layer): **Ran 30 tests in 0.257s -> OK**

**Harness contamination:** none (no file outside evals/runs/ changed during the run)


Cost: $0.57 total = $0.45 for 1 skill runs + $0.12 for 5 grader calls (total_cost_usd reported by Claude Code for each call (list prices)).

| Case | Status | Exec | Structured | Provenance | Commentary | Turns | Cost $ |
|---|---|---|---|---|---|---:|---:|
| `b_abc_rounding_vanished_lines` | **PASS** | 6/6 | 7/7 | 1/1 | 4/4 | 13 | 0.45 |

## b_abc_rounding_vanished_lines: PASS

ABC Inc, Jun 2026: expense lines that went to zero, judged under the rounding policy (generalises the Task 2 '721 -> roughly 700' instance)

Skill run: model `claude-opus-5-5`, 13 turns, 59.1 s.

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

Number provenance (P1): **PASS**, 49 matched, 26 ignored, 0 unmatched.

| Claim | Kind | Status | Grader evidence |
|---|---|---|---|
| R1: Mentions that some expense lines were zero in Jun 2026 after being non-zero in prior months, naming at least two of: Advisory Services, Federal & State Taxes, Marketing/Advertising: Miscellaneous, Professional Fees. | required | **PASS** | The commentary says "Expense lines at zero (per flags)" and names Advisory Services, Professional Fees, Federal & State Taxes and Marketing/Advertising: Miscellaneous as zero in Jun 2026 after earlier non-zero values. That is four named lines, and the rule needs two. |
| R2: Every figure given for those lines' prior averages (individually or as a range) satisfies the rounding policy. If no such figures are given, this claim PASSES. | required | **PASS** | The commentary gives "prior 6-month average 999" for Federal & State Taxes (true 998.5083, about 0.05% off) and "average 721" for Marketing Misc (true 721.0033). Both are within the 5% band. The other figures given for Advisory Services (2,500) and Professional Fees (3,773) are last non-zero values, not prior averages. |
| F1: States as fact a reason those lines went to zero (e.g. contract ended, cost cutting, vendor dropped). | forbidden | **PASS** | The commentary gives no reason for the zeros. It says only "Whether these have stopped or are timing is for the reviewer to confirm." |
| F2: Describes those lines as permanently discontinued or cancelled without leaving it to the reviewer. | forbidden | **PASS** | The commentary does not call the lines permanently discontinued or cancelled. It leaves "stopped or are timing" to the reviewer. |

## Calibration (frozen Task 2 artifact; not in the score)

`b_abc_rounding_vanished_lines` on `trend-reports/abc-inc-2026-06-trends.md @ 7f411d4`: **PASS**

| Claim | Status | Evidence |
|---|---|---|
| R1 (required) | PASS | The commentary says "Four expense lines are zero in Jun 2026 after averaging roughly 700–1,250 a month over the prior 6 months" and names all four lines, which matches the reference facts (Jun 2026 = 0, with non-zero prior averages). |
| R2 (required) | PASS | The range "roughly 700–1,250" matches the true averages of 721.0, 998.5, 1,045.5 and 1,250. The low end is 700 vs 721, a 2.9% relative difference, which is inside 5%. The high end is exact. |
| F1 (forbidden) | PASS | No cause is stated as fact. The only explanation offered is "the reviewer should check whether this is timing", which is a prompt to check, not an assertion. |
| F2 (forbidden) | PASS | The commentary does not call the lines discontinued or cancelled. It leaves the question to the reviewer: "the reviewer should check whether this is timing". |

## Grader negative controls (synthetic text; validates the grader, not in the score)

| Control | Rule | Expected | Grader | Agrees | Evidence |
|---|---|---|---|---|---|
| ctl_c_claims_clean | R1 | FAIL | FAIL | yes | The commentary never mentions the Professional Services subtotal, Mar 2026, or the 25 difference (2,225 vs 2,200); the data-quality problem is absent. |
| ctl_c_claims_clean | R2 | FAIL | FAIL | yes | No mismatch is raised, so nothing is left to the reviewer to resolve; the claim is absent. |
| ctl_c_claims_clean | F1 | FAIL | FAIL | yes | States "All data-quality checks pass and the data is fully reconciled," which is forbidden given the 25 mismatch in the reference facts. |
| ctl_c_claims_clean | F2 | PASS | PASS | yes | The commentary does not assert which figure (2,225 or 2,200) is correct and does not claim any error was corrected. |
| ctl_b_bad_rounding_and_cause | R1 | PASS | PASS | yes | Names all four lines as "zero in Jun 2026 after averaging roughly 500-1,250 a month over the prior six months", which matches the reference facts (Jun 2026 = 0, prior averages non-zero). |
| ctl_b_bad_rounding_and_cause | R2 | FAIL | FAIL | yes | The stated range "500-1,250" has a true low of 721.0033 (Marketing Misc). 500 is about 31% below that, outside the 5% band. The upper bound of 1,250 is correct. |
| ctl_b_bad_rounding_and_cause | F1 | FAIL | FAIL | yes | States as fact: "This is because those vendor contracts ended in May." That is an unsupported causal reason. |
| ctl_g_guessed_ttm | R1 | FAIL | FAIL | yes | The commentary mentions "annualising the nine months" but never acknowledges that twelve-month comparisons are unavailable because the export covers fewer than 12 months; it presents a TTM figure instead. |
| ctl_g_guessed_ttm | F1 | FAIL | FAIL | yes | It states "On a trailing-twelve-month basis, annualising the nine months gives roughly 850,000," which is a TTM/annualised estimate. |

