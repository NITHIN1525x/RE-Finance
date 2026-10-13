# Decisions summary: the 10 that matter most

One line each: the decision, why, and where it's argued in full ([DECISIONS_LOG.md](DECISIONS_LOG.md)).

| # | Decision | Why | Ref |
|---|---|---|---|
| 1 | Connect through **Intuit's official MCP server** (pinned, stdio), not the native connector, a third-party MCP or a custom one | Works with the developer sandbox, auditable source, and credentials stay ours; the native connector writes by design and doesn't document sandbox use | D-01 |
| 2 | **Read-only by not registering write tools** (three restriction flags plus a pre-flight launcher) | Intuit has no read-only OAuth scope, so read-only must be enforced in code, not left to model behaviour | D-09, D-25 |
| 3 | **Three-layer sandbox guard**: startup setting, API host allow-list, post-connect CompanyInfo check | The OAuth endpoints can't tell sandbox from production, so one check isn't enough | D-13 |
| 4 | **All secrets in one owner-only folder** (`connection/.secrets/`); humans type credentials in exactly one file | One place to protect, scan and rotate; nothing secret in code, logs or the repo | D-05, D-06 |
| 5 | **One token-refresh owner per connection** (Django ↔ MCP check-out/check-in lease) | Intuit rotates refresh tokens, and two independent refreshers strand each other | D-08, D-16 |
| 6 | **Code computes every number; Claude writes only the commentary** (JSON contract plus a narrative slot) | Figures are deterministic, testable and traceable to cells; only the prose varies | D-30, D-32 |
| 7 | **Structural subtotal rule** (stack of open sections); formatting is never trusted | Detail rows sum exactly to stated totals and survive layout changes; proven on a second company's layout | D-31, D-34 |
| 8 | **Category mapping is data** (`category_map.json`, a per-company `--config` copy), with an explicit "Other" bucket | A client's mapping gaps are fixed without code, and they stay visible to the reviewer | D-33 |
| 9 | **Evals check against facts derived from raw workbook cells**, grade commentary with a different model, and never count a grader failure as PASS | The skill can't grade itself; a broken grader shows up as BLOCKED, not as false confidence | D-40, D-41, `evals/README.md` |
| 10 | **Regression policy**: deterministic checks block on one run; a commentary flip is resampled to 4 samples (≥2 failures block) | Measured grader noise (2/4 on identical text) makes single-sample prose verdicts unreliable | D-49, D-51 |

**Incidents and corrections, recorded as they happened:**
- D-38: eval contamination in the first run.
- D-53: secret-database fragments printed to session output; key rotated, guard added.
- D-57: P1 provenance check found to be unable to fail in harness runs; not yet fixed.
