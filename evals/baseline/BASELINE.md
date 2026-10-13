# Evaluation baseline (current: v3)

| Version | Run | Why | Result | Cost | Where |
|---|---|---|---|---|---|
| **v3 (current)** | `policy-run-20261013` | After the revenue-stream "zero since" wording (D-48), the two SKILL.md commentary rules (D-50, D-51) and the resampling policy (D-49). Diff vs v2: only case a (S17/S18), as predicted | 132/132 PASS, 7/7 cases, 0 UNSTABLE, no contamination, no resampling needed | $2.95 | `evals/baseline/policy-run-20261013/` |
| v2 | `commit3-run-20261012` | After the expense-line "zero since" change (D-45/D-47) | 130/130 PASS, 7/7 | $3.04 | `evals/baseline/history/v2/` |
| v1 | `clean-run-20261012` | First uncontaminated run (D-41) | 121/121 PASS, 7/7 (P1 applied afterwards: 7/7) | $2.74 | `evals/baseline/history/v1/` |

Machine-readable pointer for the regression policy: `current.json` (→ `policy-run-20261013`). Policy: `../REGRESSION.md`.

## v3 details

| Field | Value |
|---|---|
| Source run | `evals/runs/policy-run-20261013` (git-ignored); copied verbatim to `policy-run-20261013/`, with its console log |
| Result | **132/132 checks PASS, 0 FAIL, 0 BLOCKED, 0 UNSTABLE; 7/7 cases PASS; harness contamination: none.** No commentary flip vs v2, so no case was resampled |
| Regression tests | Ran 30 tests in 0.202s -> OK |
| Grader controls | ctl_c_claims_clean AGREES, ctl_b_bad_rounding_and_cause AGREES, ctl_g_guessed_ttm AGREES |
| Git HEAD at run | `7f411d4` (later committed as ecd4507, 661f105 and the v3 commit; 12 path(s) uncommitted at run time) |
| Claude Code | `2.1.296 (Claude Code)` |
| Skill model | requested `claude-opus-5-5`, reported `claude-opus-5-5` |
| Grader model | requested `claude-sonnet-5-5`; reported in grader calls: `claude-haiku-5-5`, `claude-sonnet-5-5` |
| Run window (UTC) | 2026-10-13T02:16:56+00:00 to 2026-10-13T02:24:51+00:00 |
| Cost | **$2.95** = $2.68 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)) |
| results.json sha256 | `3fff49a9d6408062c3095ca99e8e807eb21d1a901cf28dda83eb5c65aa366a65` (LF-normalised = the committed blob) |
| Verbatim-copy fingerprint | `6ad659b2571d9d92769e62b194b100de8b31743fd804994381f7ce3de6def4f8`: sha256 over the sorted (relative path, sha256 of LF-normalised content) list of all 166 files. Identical for the source run folder |

Compare a new run with this baseline: `python evals/compare_runs.py evals/baseline/policy-run-20261013 evals/runs/<new-run>`.
