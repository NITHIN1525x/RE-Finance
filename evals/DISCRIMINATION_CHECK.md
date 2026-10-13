# Discrimination check: do the evals catch broken output?

**Date:** 2026-10-13. **Cost:** $0.17: 5 grader calls (`claude-sonnet-5-5` requested; Claude Code also reported
`claude-haiku-5-5` usage). No skill runs.

## Method
- I copied saved **baseline v4** outputs (`evals/baseline/v4-run-20261013/<case>/skill_output/`) for cases a, b and
  g to a scratch folder **outside the repo**, then broke the copies 4 ways.
- Each broken copy, plus one unmodified copy, was graded with the **existing, unmodified** grading code:
  - `run_evals.run_structured` (structured checks against `source_facts.json`);
  - `provenance.check` (P1);
  - `run_evals.grade` (the commentary grader).
- No harness, golden or baseline file was changed.
- One sample per copy. The commentary grader is a model, so a rerun can differ (D-51 measured 2/4 disagreement on a
  borderline claim). These breaks are not borderline.

## Results

| Copy | Case | What was broken | Structured | P1 | Commentary | Result | Caught by |
|---|---|---|---|---|---|---|---|
| clean | a | nothing | 18/18 | PASS | 9/9 | **PASS** | n/a (control) |
| (a) | a | Jun 2026 total revenue 195,898 → 159,898 in the JSON (`195898.16` → `159898.16`) and in the report (`195,898` → `159,898`), as an engine bug would produce | 17/18 | PASS | 7/9 | **FAIL** | **S2** (Jun 2026 total revenue); grader **R1** and **F4** ("about 18.4% off, outside the 5% band") |
| (b) | b | added "Advisory Services has been permanently discontinued." | 7/7 | PASS | 3/4 | **FAIL** | grader **F2** ("asserts permanence without leaving it to the reviewer") |
| (c) | a | added "Usage fees fell because the client changed accountants." | 18/18 | PASS | 8/9 | **FAIL** | grader **F2** ("asserts a cause as fact") |
| (d) | g | added "TTM revenue is 1,234,567." | 6/6 | **PASS (should fail)** | 1/2 | **FAIL** | grader **F1** ("a TTM figure for Bluebird") |

Every broken copy fails on the intended check, and the clean copy passes.

## Finding: P1 cannot fail in harness runs
- **The problem:**
  - `provenance.check(commentary, analysis, report_md)` matches each commentary number against the run's JSON
    *and every number in `report_md`*.
  - The harness passes the full report, and the skill writes the commentary *into* that report. So every
    commentary number is in its own source pool and matches itself.
  - Break (d) shows it: P1 matched `1,234,567` against the report text that contains the invented sentence.
- **Why the tests didn't catch it:** D-44's discrimination test planted numbers into a copy of the commentary but
  passed the *original* report, so the self-match never happened.
- **What this means for the record:**
  - P1 has passed in every run, but in real runs it cannot fail.
  - The "provenance 7/7" in the baseline is **not evidence** of number provenance.
  - The commentary grader and the structured checks are unaffected.
- **Fix demonstrated, not applied:** this task does not allow harness changes, so I didn't make it. Graded against
  the same report with the commentary section removed:
  - break (d) fails P1 (`1,234,567` unmatched);
  - the clean copy still passes, so the fix wouldn't introduce false alarms here.

  The fix is one line in the harness: build the pool from `report_md` with the commentary section removed. Plus a
  test where the planted number is inside the report.
- **Recorded in:** DECISIONS_LOG D-57.

## Reproduce
A sketch, run from the repo root with the skill's venv. Copy the outputs first; never edit the baseline:
```python
import json, sys; sys.path.insert(0, "evals")
import provenance, run_evals as H
spec = json.load(open("evals/goldens/cases.json")); facts = json.load(open("evals/goldens/source_facts.json"))
case = next(c for c in spec["cases"] if c["id"] == "g_bb_no_ttm")
md, analysis = open(COPY_MD).read(), json.load(open(COPY_JSON))           # the broken copy
commentary = H.commentary_of(md)
H.run_structured(case["structured"], analysis, md, facts, spec["tolerances"])
provenance.check(commentary, analysis, md)
H.grade(case, commentary, facts, spec["rounding_policy"], SCRATCH / "grader")   # paid: about $0.03 per call
```
