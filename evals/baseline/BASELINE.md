# Evaluation baseline (current: v4)

| Version | Run | Why | Result | Cost | Where |
|---|---|---|---|---|---|
| **v4 (current)** | `v4-run-20261013` | After the skill's environment changed: `CLAUDE.md`, the `.secrets` guard hook (D-53), an invented SKILL.md style example, the de-leaked TTM example, and reports naming the workbook file only (D-54). Diff vs v3: none, as predicted | 132/132 PASS, 7/7 cases, 0 UNSTABLE, no contamination, no resampling needed | $3.05 | `evals/baseline/v4-run-20261013/` |
| v3 | `policy-run-20261013` | After D-48, the D-50/D-51 commentary rules and the resampling policy (D-49). Its case g R1 PASS had the TTM example leak (D-54) | 132/132 PASS, 7/7 | $2.95 | `evals/baseline/history/v3/` |
| v2 | `commit3-run-20261012` | After the expense-line "zero since" change (D-45/D-47) | 130/130 PASS, 7/7 | $3.04 | `evals/baseline/history/v2/` |
| v1 | `clean-run-20261012` | First uncontaminated run (D-41) | 121/121 PASS, 7/7 (P1 applied afterwards: 7/7) | $2.74 | `evals/baseline/history/v1/` |

Machine-readable pointer for the regression policy: `current.json` (→ `v4-run-20261013`). Policy: `../REGRESSION.md`.

## v4 details

| Field | Value |
|---|---|
| Source run | `evals/runs/v4-run-20261013` (git-ignored); copied verbatim to `v4-run-20261013/`, with its console log |
| Prediction | `v4-run-20261013.prediction.txt`, written before the run: no verdict or structured change vs v3; no BLOCK. **Matched** (`compare_runs.py`: no differences) |
| Result | **132/132 checks PASS, 0 FAIL, 0 BLOCKED, 0 UNSTABLE; 7/7 cases PASS; harness contamination: none.** No commentary flip vs v3, so no case was resampled |
| Regression tests | Ran 31 tests in 0.342s -> OK |
| Grader controls | ctl_c_claims_clean AGREES, ctl_b_bad_rounding_and_cause AGREES, ctl_g_guessed_ttm AGREES |
| Git HEAD at run | `6ce42f6` (6 path(s) uncommitted at run time: the Task 4 files, including `CLAUDE.md` and `.claude/settings.json`, committed right after) |
| Claude Code | `2.1.296 (Claude Code)` |
| Skill model | requested `claude-opus-5-5`, reported `claude-opus-5-5` |
| Grader model | requested `claude-sonnet-5-5`; reported in grader calls: `claude-haiku-5-5`, `claude-sonnet-5-5` |
| Run window (UTC) | 2026-10-13T03:19:07+00:00 to 2026-10-13T03:27:20+00:00 |
| Cost | **$3.05** = $2.78 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)) |
| results.json sha256 | `a5ee773b1b067ddd056ff658610aac8eb9e331936925df808d9bf2eceaed68e5` (LF-normalised = the committed blob) |
| Verbatim-copy fingerprint | `5aee5509d91d2ecdda371179a98e567eae505e9ee3cf40bf2853e016b6d84648`: sha256 over the sorted (relative path, sha256 of LF-normalised content) list of all 166 files. Identical for the source run folder |

Compare a new run with this baseline: `python evals/compare_runs.py evals/baseline/v4-run-20261013 evals/runs/<new-run>`.
