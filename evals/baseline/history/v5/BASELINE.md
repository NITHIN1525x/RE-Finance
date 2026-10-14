# Evaluation baseline (current: v5)

| Version | Run | Why | Result | Cost | Where |
|---|---|---|---|---|---|
| **v5 (current)** | `v5-run-20261013` | After the P1 fix (D-58): P1 no longer counts the commentary as its own source, so it can fail. Diff vs v4: none, as predicted | 132/132 PASS, 7/7 cases, 0 UNSTABLE, no contamination, no resampling needed; P1 0 unmatched in every case | $2.90 | `evals/baseline/v5-run-20261013/` |
| v4 | `v4-run-20261013` | After CLAUDE.md, the guard hook, the de-leaked examples and file-name-only reports (D-55). Its P1 PASSes used the defective check (D-57); the fixed P1 re-run on its saved output also passes | 132/132 PASS, 7/7 | $3.05 | `evals/baseline/history/v4/` |
| v3 | `policy-run-20261013` | After D-48, the D-50/D-51 commentary rules and the resampling policy (D-49). Its case g R1 PASS had the TTM example leak (D-54) | 132/132 PASS, 7/7 | $2.95 | `evals/baseline/history/v3/` |
| v2 | `commit3-run-20261012` | After the expense-line "zero since" change (D-45/D-47) | 130/130 PASS, 7/7 | $3.04 | `evals/baseline/history/v2/` |
| v1 | `clean-run-20261012` | First uncontaminated run (D-41) | 121/121 PASS, 7/7 (P1 applied afterwards: 7/7) | $2.74 | `evals/baseline/history/v1/` |

Machine-readable pointer for the regression policy: `current.json` (→ `v5-run-20261013`). Policy: `../REGRESSION.md`.

## v5 details

| Field | Value |
|---|---|
| Source run | `evals/runs/v5-run-20261013` (git-ignored); copied verbatim to `v5-run-20261013/`, with its console log |
| Prediction | `v5-run-20261013.prediction.txt`, written before the run: no verdict or structured change vs v4; P1 PASS expected on all 7 cases (the fixed P1 passed the saved v1-v4 commentary 28/28); no BLOCK. **Matched** (`compare_runs.py`: no differences) |
| Result | **132/132 checks PASS, 0 FAIL, 0 BLOCKED, 0 UNSTABLE; 7/7 cases PASS; harness contamination: none.** No commentary flip vs v4, so no case was resampled |
| P1 per case | a 0 unmatched; b 0 unmatched; c 0 unmatched; d 0 unmatched; e 0 unmatched; f 0 unmatched; g 0 unmatched |
| Regression tests | Ran 31 tests in 0.472s -> OK |
| Grader controls | ctl_c_claims_clean AGREES, ctl_b_bad_rounding_and_cause AGREES, ctl_g_guessed_ttm AGREES |
| Git HEAD at run | `e89fdbf` (3 path(s) uncommitted at run time: the P1 fix, its tests and DISCRIMINATION_CHECK.md, committed right after) |
| Claude Code | `2.1.296 (Claude Code)` |
| Skill model | requested `claude-opus-5-5`, reported `claude-opus-5-5` |
| Grader model | requested `claude-sonnet-5-5`; reported in grader calls: `claude-haiku-5-5`, `claude-sonnet-5-5` |
| Run window (UTC) | 2026-10-13T16:30:52+00:00 to 2026-10-13T16:38:43+00:00 |
| Cost | **$2.90** = $2.63 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)) |
| results.json sha256 | `8b54d2551abc81917ace522848ce525ef0e577b44ff1bff287d28580032ef4a7` (LF-normalised = the committed blob) |
| Verbatim-copy fingerprint | `03a50dff06c5c81f2179e9ecff61a5b5c292aee294b435c4ff2f115e866ed6b1`: sha256 over the sorted (relative path, sha256 of LF-normalised content) list of all 166 files. Identical for the source run folder |

Compare a new run with this baseline: `python evals/compare_runs.py evals/baseline/v5-run-20261013 evals/runs/<new-run>`.
