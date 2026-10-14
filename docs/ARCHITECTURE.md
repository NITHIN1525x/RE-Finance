# Architecture

**[BUILT]** = runs and is tested in this repo. **[DESIGNED]** = design only.

## 1. Project structure
- **`connection/` (Task 1) [BUILT]:** Intuit's official MCP server (pinned, stdio, read-only, sandbox only) and a Django + React Console: OAuth, encrypted tokens, audit, one refresher per token ([CONNECTION.md](../connection/CONNECTION.md)).
- **`.claude/skills/monthly-trend-analysis/` (Task 2) [BUILT]:** a deterministic extractor computes every number; Claude writes only the commentary. Self-contained (requirements, references, 43 tests), so it can be copied. Mapping is data (`category_map.json`): client gaps get a `--config` copy, not code ([onboarding guide](ONBOARD_CLIENT.md)).
- **`evals/` (Task 3) [BUILT]:** 8 golden cases (one a prompt-injection case) checked against raw workbook cells, LLM-graded commentary, and a resampling regression policy ([REGRESSION.md](../evals/REGRESSION.md)). Baseline v6: 155/155.
- **Memory:** `CLAUDE.md` = conventions; auto-memory (outside the repo) = two notes, working style and task status. **Rule:** no client data or figures in memory, `CLAUDE.md` or skills; client facts stay in client data.

## 2. Hosting
- **Today [BUILT]:** one laptop. The MCP server runs over stdio, Django on SQLite, secrets in owner-only `connection/.secrets/`, and tokens move by manual check-out and check-in.
- **Team [DESIGNED]** ([§4](../connection/CONNECTION.md#4-team-hosting-what-i-would-build-next)): containerised MCP servers over remote HTTP behind SSO; Django on Postgres; a secrets manager; one service owning token refresh; an audit log of every tool call.
- **Team access [DESIGNED]:** the skill via the repo or a team plugin; the remote MCP server added once as an org-level connector (where the plan supports custom connectors), so nobody needs local secrets.

## 3. Ten clients: keeping data separate
```
 user (SSO) ─► Console / gateway: client = membership + explicit pick (never the model)
                 ├─► A: realm+token A · key A · MCP A · session A · data/A, reports/A, map A
                 └─► B … J: the same, one set each        audit log: user · tool · client
```
- **One QuickBooks connection per client** (realm and token), encrypted **[BUILT]**. Per-client keys are **[DESIGNED]**; today one Fernet key covers all clients.
- **The server picks the client** from the logged-in user plus an explicit selection. The realm comes from the stored connection, never the request **[BUILT, tested]**.
- **Never the model:** account names, memos and workbook text are untrusted and may hold instruction-like text, so nothing the model reads can pick or switch the client.
- **One client per Claude session or job:** one per MCP store **[BUILT]**; gateway-enforced **[DESIGNED]**.
- **Per-client folders and mapping overrides [DESIGNED]**; `data/`, `trend-reports/` are shared today.
- **Access and audit:** users see only their own clients **[BUILT, 8 isolation tests]**; Console actions are audited **[BUILT]**; per-tool-call audit by user, tool and client **[DESIGNED]**.

## 4. What breaks first at ten clients
1. **Manual token hand-over.** The local store holds one client, so every switch means stop Claude, `sync_mcp_tokens`, `export_mcp_env`. This breaks at client #2.
2. **Token refresh on one laptop.** Refresh tokens can rotate every ~24–26 h, and the old value then fails. Inactivity expiry is ~100 days, so a laptop that's off strands clients.
3. **MCP output cap.** A 12-month by-month P&L is ~21k tokens, against Claude Code's 25k cap; a larger chart of accounts goes over. One run already re-queried month by month (12 extra calls).
4. **Mapping gaps.** Workbook 2 put 3 accounts in "Other" (Instagram Ads is marketing): review each config.
5. **Commentary variance.** Flips in 2 back-to-back runs; grader split 2/4 on identical text; humans review.
6. **Eval cost.** Each per-client golden case adds ~$0.40 a run.

## 5. Cost (measured, list prices)
- **One skill run** (one client-month): $0.29–0.56, median $0.36 (59 runs), ≈ $3–6/month for 10 clients. On Sonnet 5.5: $0.13, same eval score, one run ([MODEL_COMPARISON.md](MODEL_COMPARISON.md)).
- **Full eval suite:** $2.73–3.05 (~8 min). Task 3 total: $22.99.

## 6. Honest limits
Built and tested on one sandbox company and two sample workbooks; the skill also ran once on ABC's P&L read live from a second sandbox ([STRETCH.md](STRETCH.md)). Beyond the Console's per-user scoping, the multi-client design is unbuilt and untested. A live refresh-token rotation was never observed.
