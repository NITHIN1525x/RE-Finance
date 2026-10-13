# QBO ↔ Claude exercise (RE Financial Services take-home)

Sandbox only. No real company data. Every decision, with its reasoning and evidence, is in
[`connection/DECISIONS_LOG.md`](connection/DECISIONS_LOG.md) (D-01 to D-57). The 10 that matter most, on one page:
[`connection/DECISIONS_SUMMARY.md`](connection/DECISIONS_SUMMARY.md).

| Task | Deliverable | Status |
|---|---|---|
| 1. QuickBooks Online ↔ Claude connection | [`connection/CONNECTION.md`](connection/CONNECTION.md) | Done |
| 2. Monthly trend-analysis skill | [`.claude/skills/monthly-trend-analysis/SKILL.md`](.claude/skills/monthly-trend-analysis/SKILL.md) | Done. The stretch goal is deferred (D-36) |
| 3. Evaluation suite | [`evals/README.md`](evals/README.md), [`evals/REGRESSION.md`](evals/REGRESSION.md) | Done. Baseline v4: 132/132 |
| 4. Architecture note | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Done |

**For the examiner:** [`submission/`](submission/) has one easy-to-read response file per task, generated from existing outputs by `python scripts/build_submission.py` (free); `--live-task1` re-runs the Task 1 sandbox query.

Commands are PowerShell from the repo root. On macOS/Linux, use `.venv/bin/python` wherever these say
`.venv/Scripts/python`. Prerequisites: Git, Python 3.12+, and Claude Code. Task 1 also needs Node 22+ and an
Intuit sandbox app.

## Task 1: connection
Claude reaches QuickBooks through Intuit's **official MCP server**, which is:
- pinned as a submodule at `31a1dd5`;
- run locally over stdio;
- **read-only** (the write tools are never registered) and **sandbox-only**.

A Django + React **Connection Console** handles OAuth, stores tokens Fernet-encrypted, scopes everything per
client, and makes sure only one component refreshes a token at a time.
- Setup takes about 10 minutes, but needs your own Intuit developer app: [`connection/QUICKSTART.md`](connection/QUICKSTART.md).
- Live demo: [`connection/DEMO_SCRIPT.md`](connection/DEMO_SCRIPT.md).
- Problems: [`connection/TROUBLESHOOTING.md`](connection/TROUBLESHOOTING.md).

## Task 2: trend-analysis skill
The deterministic Python extractor computes every figure, and Claude writes only the commentary. It needs no
QuickBooks connection and no secrets.

```powershell
# one-time: the skill's own environment (pinned openpyxl)
python -m venv .claude/skills/monthly-trend-analysis/.venv
.claude/skills/monthly-trend-analysis/.venv/Scripts/python -m pip install -r .claude/skills/monthly-trend-analysis/requirements.txt

# the numbers only (no Claude): the ABC workbook in data/ -> demo-output/abc-inc-2026-06-trends.{json,md}
.claude/skills/monthly-trend-analysis/.venv/Scripts/python .claude/skills/monthly-trend-analysis/scripts/run_trends.py --out-dir demo-output

# the full skill (numbers + Claude's commentary), from the repo root
claude -p "Monthly trend analysis for ABC Inc from the workbook in data/, draft for the reviewer. Save the report in demo-output/." --allowedTools "Skill Bash Read Edit Write Glob Grep"
```
- **Keep `demo-output/`** (git-ignored). Without it, the script writes to `trend-reports/` and overwrites the
  committed examples, which hold Claude's commentary, with a draft whose commentary slot is empty.
- The submodule and `connection/.secrets/` aren't needed for Tasks 2–4.
- Design, the subtotal rule and the portability results are in D-30 to D-35. Example outputs, including
  Claude's commentary, are in [`trend-reports/`](trend-reports/).

## Task 3: evaluation suite
- Seven golden cases are checked against the raw workbook cells.
- The commentary is graded by a different model.
- A resampling policy handles flips in commentary verdicts.
- Baseline and history: [`evals/baseline/BASELINE.md`](evals/baseline/BASELINE.md).

```powershell
$py = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"     # uses the skill's environment
& $py evals/goldens/derive_facts.py --check      # expected values still match the workbooks
& $py evals/run_evals.py                         # full suite: real Claude calls (Opus + Sonnet), ~8 min, ~$3
& $py evals/compare_runs.py evals/baseline/v4-run-20261013 evals/runs/<run-id>
```

## Task 4: architecture note
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): the project structure, hosting today vs for a team, and ten
clients with their data kept separate. It also answers "what breaks first at ten clients" and gives measured
costs.

## Tests (no Claude calls, no secrets needed)
```powershell
$py = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"
& $py -m unittest discover -s .claude/skills/monthly-trend-analysis/tests    # 31 skill tests
& $py -m unittest discover -s evals/tests                                   # 40 eval-side tests
python connection/scripts/test_secret_scan.py                               # 17 secret-scanner tests
python connection/scripts/test_guard_secrets_hook.py                        # 6 tests
# Task 1 backend (needs its venv; see QUICKSTART step 3):
cd connection/backend; .venv/Scripts/python manage.py test qbo --settings=config.settings_test; cd ../..   # 63 tests
```

## Conventions
- [`CLAUDE.md`](CLAUDE.md) holds conventions for Claude in this repo. It contains no client data.
- `git config core.hooksPath .githooks` enables the secret-scanning pre-commit hook (D-10, D-53).
