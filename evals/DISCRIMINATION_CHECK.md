# Discrimination check: do the evals catch broken output?

Run twice on 2026-10-13:
- **before** the P1 fix, $0.17 (D-57);
- **after** it, $0.16 (D-58).

Each run made 5 grader calls (`claude-sonnet-5-5` requested; Claude Code also reported `claude-haiku-5-5` usage) and
no skill runs.

## Method
- I copied saved **baseline v4** outputs (`<case>/skill_output/` of `v4-run-20261013`) for cases a, b and g to a
  scratch folder **outside the repo**, then broke the copies 4 ways.
- Each broken copy, plus one unmodified copy, was graded with the repo's own grading code:
  - `run_evals.run_structured` (structured checks against `source_facts.json`);
  - `provenance.check` (P1, called exactly as the harness calls it, with the full report);
  - `run_evals.grade` (the commentary grader).
- No harness, golden or baseline file was changed for the check itself. One sample per copy. The grader is a model,
  but these breaks are not borderline, and both runs gave the same verdicts.

## Results (after the fix)

| Copy | Case | What was broken | Structured | P1 | Commentary | Result | Caught by |
|---|---|---|---|---|---|---|---|
| clean | a | nothing | 18/18 | PASS | 9/9 | **PASS** | n/a (control) |
| (a) | a | Jun 2026 total revenue 195,898 → 159,898 in the JSON (`195898.16` → `159898.16`) and in the report, as an engine bug would produce | 17/18 | PASS | 7/9 | **FAIL** | **S2** (Jun 2026 total revenue); grader **R1** and **F4** ("about 18.4% off, outside the 5% band") |
| (b) | b | added "Advisory Services has been permanently discontinued." | 7/7 | PASS | 3/4 | **FAIL** | grader **F2** ("states permanence as fact") |
| (c) | a | added "Usage fees fell because the client changed accountants." | 18/18 | PASS | 8/9 | **FAIL** | grader **F2** ("asserts a cause as fact") |
| (d) | g | added "TTM revenue is 1,234,567." | 6/6 | **FAIL** | 1/2 | **FAIL** | **P1** (`1,234,567` unmatched) and grader **F1** ("a TTM figure for Bluebird") |

- Every broken copy fails on the intended check, and the clean copy passes.
- In (a), P1 correctly passes: the wrong figure appears consistently in the run's own output, so the structured
  check S2 is the one that catches an engine-level error. P1 catches numbers the commentary invents.

## What the first run found (D-57), and the fix (D-58)
- **First run:** identical verdicts, except that **P1 passed break (d)**.
  - The harness passes P1 the full report, and the skill writes its commentary into that report. So every
    commentary number matched itself, and P1 could never fail.
  - D-44's planted-number test missed this because it passed a report that did not contain the planted text.
- **Fix** (`evals/provenance.py`, `without_commentary`): P1's pool is the run's JSON plus the report with the
  commentary removed. The commentary is the section between `## 1. Commentary (draft)` and the engine's
  `### Flags raised`, plus any report line identical to a commentary line. The engine's flags and tables stay in
  the pool.
- **Tests:** `evals/tests/test_provenance.py::CommentaryCannotVouchForItself`. It fails without the fix: the old P1
  passes break (d).
  - break (d) rebuilt on the current baseline, called exactly as the harness does: FAIL, with exactly
    `1,234,567` unmatched;
  - the clean copy: PASS;
  - every current baseline case: PASS;
  - engine text still counts as a source.
- **Earlier baselines re-checked with the fixed P1:** all 7 cases of v1, v2, v3 and v4 still PASS, with 0
  unmatched. The skill's real commentary contained no unsupported numbers; P1 just couldn't have shown it.

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
provenance.check(commentary, analysis, md)                                 # free; now FAILs on break (d)
H.grade(case, commentary, facts, spec["rounding_policy"], SCRATCH / "grader")   # paid: about $0.03 per call
```
