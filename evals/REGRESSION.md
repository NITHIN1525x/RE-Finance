# Regression policy for the trend-analysis skill

How a change to the skill, goldens, grader or harness is judged against the current baseline
(`evals/baseline/current.json`). Implemented in `evals/policy.py` (tested in `evals/tests/test_policy.py`) and applied
by `evals/run_evals.py`.

## 1. Two kinds of checks, two rules

| Check type | Examples | Rule |
|---|---|---|
| **Deterministic** | execution (X1–X6), structured values (S\*), number provenance (P1) | **Hard-blocking on a single run.** Any FAIL blocks. They are not resampled: the same code on the same workbook gives the same answer. |
| **Commentary claims** | required/forbidden claims (R\*, F\*) judged by the grader | **Resampled on a flip.** A single run of LLM prose, graded by an LLM, is noisy (measured: see below). |

## 2. Commentary flips trigger resampling

- A **flip** is a commentary claim that FAILs in this run but PASSed in the baseline. A claim the baseline doesn't
  have counts as a flip, to be conservative.
- On a flip, and only if that case's deterministic checks all passed, the harness **re-runs the whole case 3 more
  times**: a real skill run plus grading each time. Each claim is then judged on all **4 samples**:

  | Failing samples (of 4) | Claim / case status | Effect |
  |---|---|---|
  | 0 | PASS | clean |
  | 1 | **UNSTABLE** | reported, **not blocking**; investigate |
  | 2 or more | **FAIL** | **blocks** the change |
  | 0, but the grader could not judge some sample | BLOCKED | never counted as a pass |

- A deterministic FAIL in **any** resample also blocks.
- The report shows each claim's pass rate (e.g. `R1 3/4`), every sample's status, and each sample's grader evidence.

## 3. What blocks a change

- Any deterministic FAIL, in any sample.
- Any commentary claim failing in 2 or more of 4 samples.
- Harness contamination: any file outside `evals/runs/` changed during the run (exit code 3). Rerun without touching
  files.
- An **unexpected diff** against the baseline: a case changes that the change's written prediction didn't name.
  Write the prediction down (DECISIONS_LOG) *before* the run. If the diff doesn't match, stop and investigate.

UNSTABLE does not block, but it is recorded in DECISIONS_LOG with the evidence.

## 4. Why this policy (DECISIONS_LOG D-49)

- **Measured noise.** In two consecutive full runs, two different cases flipped once each (case b F2, case g R1), with
  nothing relevant changed in the skill.
- **The grader disagrees with itself.** Re-grading *the identical case g commentary* gave R1 PASS, PASS, FAIL. With
  the original grading that is 2 FAIL in 4, on unchanged text.
- **A single sample is therefore weak evidence either way.** Blocking on one FAIL would block good changes;
  ignoring FAILs would miss real regressions. Four samples, with ≥2 failures to block, still lets a real regression
  through sometimes (and noise block sometimes). It is a pragmatic threshold, not a statistical guarantee.
- **Resampling only on a flip** keeps routine runs at one sample per case. A flip costs about 3 × $0.45 extra.

## 5. Updating the baseline

Only after a run with no blocking result and a diff that matches its written prediction:
1. copy the run verbatim into `evals/baseline/<run-id>/`;
2. move the previous version into `evals/baseline/history/vN/` (never overwrite it);
3. update `evals/baseline/current.json` and `BASELINE.md`;
4. record the reason in DECISIONS_LOG.
