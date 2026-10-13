# Note on this run (added afterwards; the results and report are unchanged)

**Result: FAIL, recorded as-is.** 131/132 checks. Case b passed, which was the point of this run (the zero-line
SKILL.md rule had just been added). But **case g's required claim R1 flipped PASS → FAIL**. No contamination;
cost $2.96.

- **R1:** "Acknowledges that twelve-month comparisons (TTM and/or year-over-year) are not available because the export
  covers fewer than 12 months." The commentary's only relevant sentence was "No same-month-last-year comparison is
  available, because the export starts in Jan 2026." The grader ruled it "only partly made": no TTM mention, and no
  explicit "fewer than 12 months".
- **Grader noise, measured:** re-grading this exact commentary 3 times (`evals/runs/caseg-regrade-1..3`) gave R1
  **PASS, PASS, FAIL**. With the original grading that is 2 FAIL in 4, on identical text. The verdict sits at a
  borderline.
- **Resolution** (DECISIONS_LOG D-49 to D-52): a SKILL.md rule to name the missing comparisons and the month count;
  the resampling policy for commentary flips (`evals/REGRESSION.md`); and a clean full run (`policy-run-20261013`,
  132/132), which became baseline v3. The R1 golden and rubric were deliberately **not** changed.
