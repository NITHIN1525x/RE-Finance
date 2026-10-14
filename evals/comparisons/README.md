# Model-comparison runs (not baselines)

Full eval-suite runs with the **skill** on a different model. The grader stays `claude-sonnet-5-5`, as in the
baseline. Started with `evals/run_evals.py --skill-model <model> --no-resample`, so every case has exactly one sample.
The baseline (`evals/baseline/`, `current.json`) is unchanged. The write-up is in
[`docs/MODEL_COMPARISON.md`](../../docs/MODEL_COMPARISON.md); the decision record is DECISIONS_LOG D-64.

Each folder holds the run's `results.json`, `report.md`, `manifest.json` and console log. The full run folders
(skill streams, outputs, grader calls) stayed in the git-ignored `evals/runs/`.

| Folder | Skill model | Result | Cost | Note |
|---|---|---|---|---|
| `cmp-sonnet-5-5-20261014` | claude-sonnet-5-5 | 155/155, 8/8 | $1.42 | |
| `cmp-haiku-5-5-20261014` | claude-haiku-5-5 | 153/155 raw, 6/8 | $0.43 | **The run that exposed the X3 truncation bug.** Its 2 failures (X3 on cases c and f) were false: Haiku did run `run_trends.py`, but the name crossed the 300-character cut of the stored command. Kept as found, not rescored. |
| `cmp-haiku-5-5-20261014-r2` | claude-haiku-5-5 | 154/155, 7/8 | $0.43 | Clean re-run after the X3 fix. Case c's script name crossed the cut again and X3 passed. The one failure (d:F1) is a grader self-contradiction: its evidence says "F1 should PASS", its verdict is FAIL. Recorded as returned. |
