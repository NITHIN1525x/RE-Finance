# Architecture

**[BUILT]** = runs and is tested in this repo. **[DESIGNED]** = design only.

## 1. Project structure (files, skills, memory)
- **`connection/` (Task 1) [BUILT]:** Intuit's official MCP server (pinned, stdio, read-only, sandbox only) and a Django + React Console: OAuth, encrypted tokens, audit, one token refresher ([CONNECTION.md](../connection/CONNECTION.md)).
- **`.claude/skills/monthly-trend-analysis/` (Task 2) [BUILT]:** code computes every number, Claude writes only the commentary; self-contained, 44 tests. The category map is data: a new client gets a `--config`, not code ([onboarding](ONBOARD_CLIENT.md)).
- **`evals/` (Task 3) [BUILT]:** 8 golden cases (one prompt injection) checked against raw cells, graded commentary, a regression policy ([REGRESSION.md](../evals/REGRESSION.md)). Baseline v6: 155/155.
- **Memory:** `CLAUDE.md` = conventions; auto-memory (outside the repo) = working style, task status; no client data.

## 2. Hosting
- **Today [BUILT]:** one laptop: MCP server over stdio, Django on SQLite, secrets in owner-only `connection/.secrets/`, tokens moved by manual check-out and check-in.
- **Team [DESIGNED]** ([§4](../connection/CONNECTION.md#4-team-hosting-what-i-would-build-next)): containerised MCP servers over remote HTTP behind SSO, Django on Postgres, a secrets manager, one token-refresh service. The skill ships in the repo or a plugin; the MCP server is an org connector, so nobody holds local secrets.

## 3. Ten clients: keeping data separate
```
user (SSO) -> Console / gateway: client = membership + explicit pick
                |-> A: realm+token A, key A, MCP A, session A, folders A
                '-> B ... J: one set each    audit: user, tool, client
```
- **One QuickBooks connection per client**, encrypted **[BUILT]**; per-client keys **[DESIGNED]**.
- **The server picks the client** from the user plus an explicit selection; the realm comes from the stored connection, never the request **[BUILT, tested]** or the model (workbook text is untrusted).
- **One client per Claude session:** one per MCP store **[BUILT]**, gateway-enforced **[DESIGNED]**; per-client folders and mappings **[DESIGNED]**.
- **Access and audit:** users see only their clients **[BUILT, 8 isolation tests]**; Console actions audited **[BUILT]**; per-tool-call audit **[DESIGNED]**.

## 4. What breaks first at ten clients
1. **Manual token hand-over:** the local store holds one client, so each switch is stop Claude, `sync_mcp_tokens`, `export_mcp_env`. Breaks at client #2.
2. **Laptop token refresh:** tokens can rotate every ~24–26 h; ~100 days idle expires them. **MCP output cap:** a 12-month P&L is ~21k of a 25k-token cap; larger charts go over.
3. **Mapping gaps:** workbook 2 put 3 accounts in "Other": review each client's config.
4. **Commentary variance:** flips between runs; humans review. **Eval cost:** ~$0.40 per extra golden case per run.

## 5. Cost (measured, list prices)
- **One skill run** (one client-month, Opus 5.5): $0.29–0.56, median $0.36 (74 runs), ≈ $3–6 a month for 10 clients; Sonnet 5.5 $0.13, same score, one run ([comparison](MODEL_COMPARISON.md)).
- **Full eval suite** (v6, 8 cases): $3.31, ~10 min. Eval spend to date: $34.86.

## 6. Honest limits
Tested on one sandbox company, one real workbook and two synthetic ones, plus one live run from a second sandbox ([STRETCH.md](STRETCH.md)). The multi-client design is unbuilt and untested beyond per-user scoping; no live token rotation was seen.
