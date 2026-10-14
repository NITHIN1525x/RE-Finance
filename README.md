# QBO ↔ Claude exercise (RE Financial Services take-home)

[![CI](https://github.com/NITHIN1525x/RE-Finance/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/NITHIN1525x/RE-Finance/actions/workflows/ci.yml)

This project has four parts:
1. **Connection:** a QuickBooks Online sandbox connected to Claude through Intuit's official MCP server, read-only
   and sandbox-only.
2. **Skill:** a Claude skill that turns a monthly financial-statements workbook into a trend report. Code computes
   every number; Claude writes only the commentary.
3. **Evals:** an evaluation suite that checks both the numbers and the commentary.
4. **Architecture note:** one page on structure, hosting and ten clients.

**Headline results:**
- The Task 2 stretch goal matches the workbook run to the cent in all 18 months, on live QuickBooks data.
- The eval baseline v6 scores **155/155** checks across 8 cases.

Sandbox only; no real company data.

## Start here

| What | Where | How |
|---|---|---|
| One response file per task | [`submission/`](submission/) | Task 1–3 responses, the Task 2 PDF, one file per eval case (Task 3.1–3.8), the Q&A log |
| The same files in a browser | Results page | `npm --prefix connection/frontend run dev`, then open http://localhost:5173/#results |
| A free end-to-end run | [`demo.ps1`](demo.ps1) | `powershell -ExecutionPolicy Bypass -File .\demo.ps1` |

**Conventions for the commands below:**
- **Shell:** commands are Windows PowerShell, run from the repo root.
- **Prerequisites:** Git, Python 3.12+ and Claude Code. Task 1 and the Results page also need Node 22+, and Task 1
  needs your own Intuit sandbox app.
- **Paid commands:** only the ones marked **paid** call Claude.
- **One-time setup** for the skill's environment, which the Task 2 and Task 3 commands use:

```powershell
python -m venv .claude/skills/monthly-trend-analysis/.venv
$py = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"
& $py -m pip install -r .claude/skills/monthly-trend-analysis/requirements.txt -r .claude/skills/monthly-trend-analysis/requirements-dev.txt
npm --prefix connection/frontend ci          # only for the Results page and the frontend checks
```

## Task 1: QuickBooks Online ↔ Claude connection

**What the brief asked:** "Connect your QuickBooks sandbox to Claude, securely and reliably. Your choice of method — a
native connector, an open-source MCP server you deploy, or a custom MCP built on the QuickBooks API. Demonstrate the
connection working against the sandbox. Document what you chose, what you rejected, and why — including where this
would run if a whole team (not just your laptop) needed to use it, and how credentials are handled throughout."

**What I built**
- **MCP server:** Intuit's official server, pinned as a submodule at `31a1dd5` and run locally over stdio.
- **Read-only by construction:** the write tools are never registered (71 of 142 tools load), and the launcher
  refuses to start if any restriction flag is missing.
- **Sandbox only:** a startup setting, an API host allow-list and a check of the company after connecting.
- **Connection Console (Django + React):** OAuth with a `state` check, Fernet-encrypted tokens, an audit log, and
  every record scoped per client.
- **One token-refresh owner at a time:** the token is checked out to the MCP server and checked back in, because
  Intuit rotates refresh tokens and two refreshers would strand each other.

**Where it is**

| Path | What it is |
|---|---|
| [`connection/CONNECTION.md`](connection/CONNECTION.md) | The options compared, the choice and its trade-offs |
| [`connection/quickbooks-online-mcp-server/`](connection/quickbooks-online-mcp-server/) | Intuit's MCP server (pinned submodule, not modified) |
| [`.mcp.json`](.mcp.json), [`connection/scripts/mcp_launch.mjs`](connection/scripts/mcp_launch.mjs) | How Claude Code starts the server, with the sandbox and read-only pre-flight checks |
| [`connection/backend/`](connection/backend/), [`connection/frontend/`](connection/frontend/) | The Connection Console: Django API and React UI |
| [`connection/scripts/smoke_test`](connection/scripts/smoke_test) | Live read-only checks through the same launcher Claude uses |
| [`connection/QUICKSTART.md`](connection/QUICKSTART.md) | Setup with your own Intuit app (about 10 minutes) |

**How to run / check it.** First complete [`QUICKSTART.md`](connection/QUICKSTART.md) steps 1–5 (your Intuit app,
the Console, connecting the sandbox). Then:

```powershell
connection\backend\.venv\Scripts\python connection\backend\manage.py export_mcp_env --client abc-inc-sandbox   # hand the token to the MCP server
connection\backend\.venv\Scripts\python connection\scripts\smoke_test --client abc-inc-sandbox
claude                                  # in the repo root: /mcp shows "quickbooks-sandbox: connected, 71 tools"
connection\backend\.venv\Scripts\python connection\backend\manage.py sync_mcp_tokens --client abc-inc-sandbox  # hand back, after closing Claude Code
```

**A good result:**
- the smoke test reports 11 passed, or 10 passed and 1 skipped (the Django check is skipped while the token is
  checked out, D-16);
- Claude answers questions such as *"What was net income in the sandbox last quarter?"*

**Evidence**
- **Tests:** 63 backend tests.
- **Latest live query:** the smoke test returned 10 passed, 1 skipped, 0 failed
  ([`submission/Task 1 response.md`](<submission/Task 1 response.md>)).
- **Claude runs:** three Claude Code runs, with every figure matching a separately computed ground truth
  ([`connection/evidence/phase5_ground_truth.md`](connection/evidence/phase5_ground_truth.md)).
- **Docs:** demo script [`connection/DEMO_SCRIPT.md`](connection/DEMO_SCRIPT.md), troubleshooting
  [`connection/TROUBLESHOOTING.md`](connection/TROUBLESHOOTING.md), decisions D-01 to D-29.

**Honest limits.** Tested on one sandbox company (a second was used only for the stretch goal). There is no
per-tool-call audit yet, and a live refresh-token rotation was never observed.

## Task 2: Monthly trend-analysis skill

**What the brief asked:** "Build a Claude skill that produces a monthly trend analysis from the provided Excel workbook,
for a human reviewer to finish: revenue, margins, and operating expenses by category, with month-over-month and
trailing-twelve-month views, and short written commentary flagging the movements a business owner should know about.
Structure it so a teammate could read, maintain, and extend it — and point it at a different company's data without a
rewrite. Stretch goal: load the workbook's data into your sandbox and run the same skill end-to-end through the live
connection."

**What I built**
- **Engine:** a deterministic Python engine computes every figure from the workbook:
  - revenue by stream, month-over-month, TTM and year-over-year;
  - gross margin and operating expenses by category;
  - net income and cash;
  - data-quality cross-checks.
- **Commentary:** Claude writes only the 4–8 commentary bullets, in a marked slot, from the engine's flags. The JSON
  output is the source of truth.
- **Reading the sheet:** rows are classified by structure (header, detail, total), never by formatting. A subtotal
  that doesn't match its detail rows is reported, not silently resolved.
- **Other companies:** a new company's export works without code changes. The category map is data, and a
  synthetic second company, Bluebird, is part of the tests.
- **PDF:** an optional printable report, built only from the JSON.
- **Stretch goal (done):** ABC's P&L was loaded into a new sandbox company, read back through the read-only MCP
  server, and analysed by the unchanged skill. Result: 21 metrics × 18 months, 0 differences
  ([`docs/STRETCH.md`](docs/STRETCH.md)).

**Where it is**

| Path | What it is |
|---|---|
| [`.claude/skills/monthly-trend-analysis/SKILL.md`](.claude/skills/monthly-trend-analysis/SKILL.md) | The skill's instructions to Claude |
| [`.claude/skills/monthly-trend-analysis/scripts/`](.claude/skills/monthly-trend-analysis/scripts/) | `run_trends.py` (the engine CLI), `render_pdf.py`, and the `trends/` package |
| [`.claude/skills/monthly-trend-analysis/references/`](.claude/skills/monthly-trend-analysis/references/) | The extraction rules and the category map |
| [`.claude/skills/monthly-trend-analysis/tests/`](.claude/skills/monthly-trend-analysis/tests/) | The skill's tests and the synthetic test workbooks |
| [`data/`](data/) | The ABC Inc workbook |
| [`trend-reports/`](trend-reports/) | Example outputs, including Claude's commentary |
| [`stretch/`](stretch/), [`docs/STRETCH.md`](docs/STRETCH.md) | The stretch-goal scripts and write-up |

**How to run / check it**

```powershell
$py = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"
& $py .claude/skills/monthly-trend-analysis/scripts/run_trends.py --out-dir demo-output     # numbers only, free
& $py .claude/skills/monthly-trend-analysis/scripts/render_pdf.py demo-output/abc-inc-2026-06-trends.json   # optional PDF, free
claude -p "Monthly trend analysis for ABC Inc from the workbook in data/, draft for the reviewer. Save the report in demo-output/." --allowedTools "Skill Bash Read Edit Write Glob Grep"   # paid: the full skill
```

**A good result:**
- the engine prints `Company: ABC Inc | months: Jan 2025 - Jun 2026 (18) | balance sheet: yes` and
  `data-quality mismatches: 0`;
- it writes `demo-output/abc-inc-2026-06-trends.json` and `.md`.

Keep `--out-dir demo-output` (git-ignored). Without it, the engine writes to `trend-reports/` and overwrites the
committed examples.

**Evidence**
- **Tests:** 44 skill tests, 12 of them for the PDF.
- **Jun 2026 figures from the engine:** revenue 195,898.16 (−6.0% vs May 2026), gross margin 70.2%, net income
  −330,756.08.
- **Responses:** [`submission/Task 2 response.md`](<submission/Task 2 response.md>) and
  [`submission/Task 2 report.pdf`](<submission/Task 2 report.pdf>).
- **Docs:** the extraction rules
  ([`references/extraction-rules.md`](.claude/skills/monthly-trend-analysis/references/extraction-rules.md)), design
  decisions D-30 to D-35, and the stretch goal D-62.

**Honest limits.** Tested on one real workbook and two synthetic ones. Other QuickBooks export layouts may need a
`--config` category map or produce parser warnings. The commentary is a draft for a human reviewer.

## Task 3: Evaluation suite

**What the brief asked:** "Build an eval suite. At least five golden cases — a data state paired with the expected
analysis output — and a concrete description of how you'd grade the system against them and how you'd detect a
regression after a future change."

**What I built**
- **Golden cases:** 8 cases that run the real skill end to end with `claude -p`: ABC, Bluebird, and a synthetic
  prompt-injection workbook (case h).
- **Expected values:** taken from the raw workbook cells by a separate script, never from the skill's code. Each
  fact records its sheet, cells and formula.
- **Four layers of checks:**
  - execution (did the skill and the script run, and where did files land);
  - structured values against the facts;
  - P1 (every number in the commentary must appear in the run's own output);
  - required and forbidden commentary claims, graded by a different model (Sonnet grades Opus).
- **Grader and harness safeguards:** 5 grader controls with known verdicts, a guard against repo changes during a
  run, and a resampling policy for commentary verdicts that flip.
- **Baselines:** versioned, v1 to v6, each with a prediction written before the run.

**Where it is**

| Path | What it is |
|---|---|
| [`evals/README.md`](evals/README.md) | How the suite works, every check, and its limits |
| [`evals/goldens/`](evals/goldens/) | `cases.json` (the cases), `source_facts.json` and `derive_facts.py` (expected values from the cells) |
| [`evals/run_evals.py`](evals/run_evals.py), [`evals/grader_prompt.md`](evals/grader_prompt.md) | The harness and the grader instructions |
| [`evals/REGRESSION.md`](evals/REGRESSION.md) | The resampling and regression policy |
| [`evals/baseline/BASELINE.md`](evals/baseline/BASELINE.md) | The current baseline (v6) and its history |
| [`evals/DISCRIMINATION_CHECK.md`](evals/DISCRIMINATION_CHECK.md) | Evidence that the checks fail on broken output |

**How to run / check it**

```powershell
$py = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"
& $py evals/goldens/derive_facts.py --check                                       # free: expected values still match the workbooks
& $py evals/compare_runs.py evals/baseline/history/v5/v5-run-20261013 evals/baseline/v6-run-20261014   # free: v5 vs v6
& $py evals/provenance.py evals/baseline/v6-run-20261014                          # free: P1 on the saved baseline
& $py evals/run_evals.py                                                          # paid: the full suite, about 10 minutes
```

**A good result:**
- `source_facts.json matches the workbooks`;
- `compare_runs` shows `NEW v6-run-20261014: score 155/155, cases 8/8`;
- `provenance` shows `UNMATCHED 0` for every case;
- a full run ends with `score: 155/155 checks PASS` and exit code 0.

**Evidence**
- **Baseline v6:** 155/155 checks, 8/8 cases, no resampling, no contamination, $3.31
  ([`BASELINE.md`](evals/baseline/BASELINE.md)).
- **Tests:** 62 eval-side tests, for the harness, P1, the policy and the submission files.
- **Discrimination check:** the 4 deliberately broken copies each fail on the intended check, and the clean copy
  passes.
- **Per-case results:** [`submission/Task 3 response.md`](<submission/Task 3 response.md>), with one file per case
  in `submission/Task 3.1.md` to `Task 3.8.md`.

**Honest limits.** Each case gets one sample per run unless a commentary verdict flips. The grader is a model: in
one comparison run it contradicted its own evidence (D-64).

## Task 4: Architecture note

**What the brief asked:** "Write one page on your architecture: how you structured the project (files, skills,
memory), your hosting choices, and what changes when this runs for ten different clients — including how you'd keep
each client's data separate."

**What I built:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), one page in six sections:
1. Project structure;
2. Hosting, today and for a team;
3. Ten clients, with their data kept separate;
4. What breaks first at ten clients;
5. Measured cost;
6. Honest limits.

Each component is marked **[BUILT]** (runs and is tested here) or **[DESIGNED]** (design only).

**Where it is**

| Path | What it is |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The note |
| [`docs/MODEL_COMPARISON.md`](docs/MODEL_COMPARISON.md) | The measured cost per model, linked from the note's cost section |

**How to run / check it.** Read it; it fits on one page (42 lines). Every cost figure comes from measured runs.

**Evidence**
- **Cost per report:** one skill run (one client-month) costs $0.29–0.56, median $0.36 over 59 runs, which is about
  $3–6 a month for 10 clients.
- **On Sonnet 5.5:** $0.134 per report with the same eval score, over one run
  ([`MODEL_COMPARISON.md`](docs/MODEL_COMPARISON.md)).

**Honest limits.** Beyond the Console's per-user scoping, the multi-client design is unbuilt and untested.

## Additional features (beyond the brief)

| Feature | What it does | Why it matters | Where |
|---|---|---|---|
| PDF report | Optional printable report, built only from the skill's JSON, with the commentary labelled as a draft | A reviewer can print or send it; no number is typed in by hand | [`render_pdf.py`](.claude/skills/monthly-trend-analysis/scripts/render_pdf.py), [`Task 2 report.pdf`](<submission/Task 2 report.pdf>), D-61 |
| Results page, Q&A tab and `/log-answer` | A read-only browser view of `submission/`; `/log-answer` appends a checked question and answer to the Q&A log | The examiner can browse every result in one place; answers are logged verbatim, never retyped | [`connection/frontend/`](connection/frontend/), [`.claude/commands/log-answer.md`](.claude/commands/log-answer.md), [`scripts/log_answer.py`](scripts/log_answer.py), D-60 |
| CI | Runs every free test, the frontend lint and build, and the secret scan on each push and pull request | Catches breakage without a local setup | [`.github/workflows/ci.yml`](.github/workflows/ci.yml), D-59 |
| One-command demo | Checks the token owner, runs the live smoke test and the engine, prints the key figures and rebuilds `submission/` | A free end-to-end check in one command; it never hands tokens over | [`demo.ps1`](demo.ps1), D-59 |
| New-client guide | How to run the skill on another company's export without code changes | Shows the skill isn't tied to ABC | [`docs/ONBOARD_CLIENT.md`](docs/ONBOARD_CLIENT.md) |
| Prompt-injection test (case h) | A synthetic workbook whose account name and footer memo tell the AI to misreport the results | Shows the skill treats workbook text as data | [`build_injection_workbook.py`](.claude/skills/monthly-trend-analysis/tests/build_injection_workbook.py), [`Task 3.8.md`](<submission/Task 3.8.md>), D-63 |
| Model comparison | The full suite run with the skill on Sonnet 5.5 and Haiku 5.5, against the Opus baseline | Shows the cost and quality trade-off for choosing a model | [`docs/MODEL_COMPARISON.md`](docs/MODEL_COMPARISON.md), [`evals/comparisons/`](evals/comparisons/), D-64 |
| Discrimination check | Deliberately broken outputs graded with the suite's own code | Shows the checks fail when they should; it found and fixed a P1 defect | [`evals/DISCRIMINATION_CHECK.md`](evals/DISCRIMINATION_CHECK.md), D-57, D-58 |
| Secrets guard hook and secret scanner | A Claude Code hook blocks tools from reading `connection/.secrets/`; the scanner reports location and rule only, and a pre-commit hook runs it | Secrets can't be read, printed or committed by accident | [`guard_secrets_hook.py`](connection/scripts/guard_secrets_hook.py), [`secret_scan`](connection/scripts/secret_scan), [`.githooks/pre-commit`](.githooks/pre-commit), D-10, D-53 |
| Decisions log and summary | Every decision with its alternatives and evidence, plus the 10 that matter most on one page | Shows the reasoning behind each choice | [`DECISIONS_LOG.md`](connection/DECISIONS_LOG.md), [`DECISIONS_SUMMARY.md`](connection/DECISIONS_SUMMARY.md) |

## Repository map

```text
.claude/        the skill (skills/monthly-trend-analysis/), the /log-answer command, the secrets guard hook settings
.github/        CI workflow
.githooks/      pre-commit secret scan
connection/     Task 1: MCP server (submodule), Django backend, React frontend, scripts, connection docs, decisions log
data/           the ABC Inc workbook
docs/           architecture note, stretch goal, model comparison, new-client guide
evals/          Task 3: golden cases, harness, baselines, comparison runs, eval tests
scripts/        submission builder and the Q&A-log writer
stretch/        Task 2 stretch-goal scripts (load, read back, adapt, compare)
submission/     one generated response file per task, for the examiner
trend-reports/  example skill outputs with Claude's commentary
CLAUDE.md       conventions for Claude in this repo (no client data)
demo.ps1        the one-command demo
```

## Tests

None of these calls Claude or needs secrets. CI runs all of them on every push and pull request. First set
`$py = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"`.

| Suite | Command | Count |
|---|---|---|
| Skill (engine and PDF) | `& $py -m unittest discover -s .claude/skills/monthly-trend-analysis/tests` | 44 |
| Eval side (harness, P1, policy, submission files) | `& $py -m unittest discover -s evals/tests` | 62 |
| Golden facts still match the workbooks | `& $py evals/goldens/derive_facts.py --check` | 1 check |
| Q&A-log writer | `& $py scripts/test_log_answer.py` | 6 |
| Secret scanner | `& $py connection/scripts/test_secret_scan.py` | 17 |
| Secrets guard hook | `& $py connection/scripts/test_guard_secrets_hook.py` | 6 |
| Stretch goal (offline) | `& $py stretch/test_stretch.py` | 13 |
| Task 1 backend (needs its venv, QUICKSTART step 3) | `Push-Location connection/backend; .venv/Scripts/python manage.py test qbo --settings=config.settings_test; Pop-Location` | 63 |
| Frontend lint and build | `npm --prefix connection/frontend run lint; npm --prefix connection/frontend run build` | pass/fail |
| Secret scan, tracked and untracked files | `& $py connection/scripts/secret_scan --all` | clean |

Total: 211 tests. To rebuild `submission/` from the saved outputs (free), run `& $py scripts/build_submission.py`.
`--live-task1` re-runs the Task 1 sandbox query.

## Security and credentials

- **Sandbox only.** The backend refuses to start for anything else, every API call goes to the sandbox host, and the
  company is checked after connecting ([D-13](connection/DECISIONS_LOG.md)).
- **Read-only.** Intuit has no read-only OAuth scope, so read-only is enforced in code: the write tools are never
  registered, and the launcher refuses to start without all three restriction flags ([D-09](connection/DECISIONS_LOG.md)).
- **Encrypted tokens.** OAuth tokens are stored Fernet-encrypted, and the browser only ever holds an HttpOnly session
  cookie ([`CONNECTION.md`](connection/CONNECTION.md)).
- **One secrets folder.** Every secret lives in the owner-only, git-ignored `connection/.secrets/`; nothing secret is
  in code, logs or the repo.
- **Scanner and hooks.** `secret_scan` reports location and rule only, never the value. The pre-commit hook runs it
  (enable it with `git config core.hooksPath .githooks`), and a Claude Code hook blocks tool access to
  `connection/.secrets/` ([`.claude/settings.json`](.claude/settings.json)).
- **Incident record.** Fragments of the local secrets database were once printed into a session's output. What
  happened, what was rotated and what changed are in [D-53](connection/DECISIONS_LOG.md).

## Decisions

- **Summary:** [`connection/DECISIONS_SUMMARY.md`](connection/DECISIONS_SUMMARY.md) has the 10 decisions that matter
  most, on one page.
- **Full log:** [`connection/DECISIONS_LOG.md`](connection/DECISIONS_LOG.md) has every decision, D-01 to D-64, with
  its reasoning, the alternatives rejected and the evidence.
- **Conventions:** [`CLAUDE.md`](CLAUDE.md) holds the conventions for Claude in this repo.
