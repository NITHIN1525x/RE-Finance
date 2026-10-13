# Note on this run (added afterwards; the results and report are unchanged)

**Result: FAIL, recorded as-is.** 131/132 checks; case b's commentary rule **F2** flipped PASS → FAIL. No
contamination; cost $2.99.

- **Prediction** (DECISIONS_LOG D-48, written before the run): only case a would change (new S17/S18). Case a
  changed exactly as predicted, but case b also flipped, so the diff did not match.
- **F2 evidence:** the commentary headed the zero-expense-lines bullet "**Expense lines no longer recurring:**". The
  grader: *"asserts that the lines have stopped recurring, which implies they have been discontinued. It does not
  leave this to the reviewer."* Case b's structured checks (S1–S7) and P1 were unchanged and passed. The code change
  in this commit touches only revenue-stream flag text.
- **Why it blocked:** the regression policy treats an unexpected PASS→FAIL flip as blocking. This change was
  therefore **not accepted on this run**, and no baseline was made from it.
- **How it was resolved** (later commits): 5 + 5 case b runs before/after a SKILL.md rule ("a zero is an
  observation, not a conclusion"), a resampling policy for commentary flips (`evals/REGRESSION.md`), and a clean
  full run (`policy-run-20261013`, 132/132), which became baseline v3. See D-48 to D-52.
