# Evaluation baseline (current: v2)

| Version | Run | Why | Result | Cost | Where |
|---|---|---|---|---|---|
| **v2 (current)** | `commit3-run-20261012` | After the intentional "vanished: has been zero since" change (DECISIONS_LOG D-45). Diff vs v1: only case b, as predicted (D-47) | 130/130 PASS, 7/7 cases, no contamination | $3.04 | `evals/baseline/commit3-run-20261012/` |
| v1 | `clean-run-20261012` | First uncontaminated run (D-41) | 121/121 PASS, 7/7 cases (P1 applied afterwards: 7/7) | $2.74 | `evals/baseline/history/v1/` (its BASELINE.md is unchanged) |

## v2 details

| Field | Value |
|---|---|
| Source run | `evals/runs/commit3-run-20261012` (git-ignored); copied verbatim to `commit3-run-20261012/`, with its console log |
| Result | **130/130 checks PASS, 0 FAIL, 0 BLOCKED; 7/7 cases PASS; harness contamination: none.** It includes the live P1 provenance check in every case and case b's new S6/S7 |
| Regression tests | Ran 29 tests in 0.225s -> OK |
| Grader controls | ctl_c_claims_clean AGREES, ctl_b_bad_rounding_and_cause AGREES, ctl_g_guessed_ttm AGREES |
| Git HEAD at run | `ae20005` (commit 3 changes uncommitted at the time: 7 path(s)) |
| Claude Code | `2.1.296 (Claude Code)` |
| Skill model | requested `claude-opus-5-5`, reported `claude-opus-5-5` |
| Grader model | requested `claude-sonnet-5-5`; reported in grader calls: `claude-haiku-5-5`, `claude-sonnet-5-5` |
| Run window (UTC) | 2026-10-12T12:10:32+00:00 to 2026-10-12T12:19:14+00:00 |
| Cost | **$3.04** = $2.77 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)) |
| results.json sha256 | `56d25a473072ed89342f4693e5f6f1379df6013a6666c86ea5bbbe6b6639b9dc` (LF-normalised = the committed blob) |
| Verbatim-copy fingerprint | `56bc88a7f207c31260cab60fbb8b06cb4cbbbedd21e96bc0f5f68a36c1afef8a`: sha256 over the sorted (relative path, sha256 of LF-normalised content) list of all 159 files. Identical for the source run folder |

Compare a new run with this baseline using `python evals/compare_runs.py evals/baseline/commit3-run-20261012 evals/runs/<new-run>`.
