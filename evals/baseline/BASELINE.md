# Evaluation baseline

| Field | Value |
|---|---|
| Source run | `evals/runs/clean-run-20261012` (copied verbatim into `clean-run-20261012/`, with its console log) |
| Why this run | It is the first **uncontaminated** full run. The first run (`first-run-20261012`) had one FAIL caused by the operator editing `evals/README.md` mid-run (see its NOTE.md). DECISIONS_LOG D-41. |
| Result | **121/121 checks PASS, 0 FAIL, 0 BLOCKED; 7/7 cases PASS; harness contamination: none** |
| Regression tests | Ran 28 tests in 0.526s -> OK |
| Grader controls | ctl_c_claims_clean AGREES, ctl_b_bad_rounding_and_cause AGREES, ctl_g_guessed_ttm AGREES |
| Git HEAD at run | `396f17d` (Task 3 files uncommitted at the time: 8 path(s)) |
| Claude Code | `2.1.296 (Claude Code)` |
| Skill model | requested `claude-opus-5-5`, reported `claude-opus-5-5` |
| Grader model | requested `claude-sonnet-5-5`; models reported in grader calls: `claude-haiku-5-5`, `claude-sonnet-5-5` (Claude Code uses Haiku for small background work) |
| Run window (UTC) | 2026-10-12T11:29:01+00:00 to 2026-10-12T11:35:54+00:00 |
| Cost | **$2.74** = $2.47 for 7 skill runs + $0.27 for 11 grader calls (total_cost_usd reported by Claude Code for each call (list prices)) |
| results.json sha256 | `fe4912c8c5d0f6143453033a93c91175925e2950b5e116e1029706205f6f462a` (LF line endings, i.e. exactly the committed blob) |
| Verbatim-copy fingerprint | `9cbb8c42a1b4c897f193c6dd2adcd8acf91cb7bf9346b38c1123a95a95490f2e`: the sha256 over the sorted (relative path, sha256 of LF-normalised content) list of all 152 files. It is identical for `evals/baseline/clean-run-20261012/` and the source `evals/runs/clean-run-20261012/`. The source folder is git-ignored and not committed; this copy is the committed record. |
| Hashing note | The harness wrote these files with Windows CRLF endings, and `.gitattributes` stores text as LF. Hashes are therefore computed after CRLF→LF normalisation, so they verify on a fresh checkout. An earlier draft of this table hashed the raw CRLF bytes, which would not have verified. |

Compare a future run with this baseline case by case and claim by claim. A single run is one sample:
the first two runs already show that commentary content varies even when every verdict agrees (D-43).
