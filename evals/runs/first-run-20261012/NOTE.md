# Note on this run (added afterwards; the results and report are unchanged)

**Case `a_abc_jun2026_core`, check X5 FAIL, is run contamination caused by the operator, not a skill
defect and not a wrong golden.**

- X5 checks that nothing outside `evals/runs/` changes during a skill run. The one change it reported was
  `?? evals/README.md`.
- That file was written by the operator (the Claude Code build session, via its Write tool) **at
  13:28:27 IST (07:58:27 UTC)**. That was while case a's skill run was in progress: the run started at
  13:27:52 IST (prompt written) and ended at 13:28:34 IST (stream written). Times are file mtimes,
  checked after the run.
- The skill run's own file edits (from `a_abc_jun2026_core/skill_run/run_meta.json` → `tool_calls`)
  were a single `Edit` of its own report,
  `evals/runs/first-run-20261012/a_abc_jun2026_core/skill_output/abc-inc-2026-06-trends.md`. None of
  its Bash commands referenced any README.
- All other checks for case a passed: 16/16 structured and 9/9 commentary. The check itself behaved
  correctly; it caught a real out-of-band change.

**Follow-up:** the harness now snapshots file contents outside `evals/runs/` and reports
`harness contamination: <path> modified during run` separately from the skill's checks. A clean full
rerun is `evals/runs/clean-run-20261012/`. See `connection/DECISIONS_LOG.md`, D-37 to D-43.
