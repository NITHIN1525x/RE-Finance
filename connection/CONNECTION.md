# Task 1: Connecting QuickBooks Online to Claude

**Choice:** Intuit's official open-source MCP server ([`intuit/quickbooks-online-mcp-server`](https://github.com/intuit/quickbooks-online-mcp-server),
pinned at `31a1dd5`), run locally over stdio in **read-only, sandbox-only** mode. A small Django + React
"Connection Console" owns OAuth, keeps tokens encrypted, and decides which component may refresh them.

**Status:** working end to end against the sandbox (Sandbox Company US 1bad):
- backend: 63 unit tests;
- smoke test: 11/11 checks;
- three Claude Code runs, with every figure matching a separately computed ground truth
  (`evidence/phase5_ground_truth.md`).

Every decision, including the alternatives I rejected, is in `DECISIONS_LOG.md` (D-01 … D-29).

## 1. Options compared

| | (a) Native Claude connector (Intuit) | **(b) Official MCP server + Console** | (c) Third-party hosted MCP/sync | (d) Custom MCP on the QBO API |
|---|---|---|---|---|
| Setup effort | Lowest: sign in at claude.ai › Connectors | Medium: Intuit app, OAuth console, build, `.mcp.json` | Low–medium: vendor account + OAuth | Highest: write and test every tool |
| Developer **sandbox** | **Not documented**; see note | **Yes** (verified live) | Varies by vendor | Yes |
| Read-only control | Per-tool settings in Claude; the connector itself writes (create/update/delete invoices and estimates since 2026-07-28) | **Tools never registered** (`QUICKBOOKS_DISABLE_*=true`, verified: 71 of 142 tools); launcher refuses otherwise | Vendor-dependent (e.g. CData's open-source server is read-only; Pipedream exposes actions) | By construction |
| Where credentials live | Intuit / Anthropic | **Our** encrypted DB + an owner-only token file | The vendor (an extra data processor) | Ours |
| Auditability | Claude-side only | Console audit log for OAuth, refresh, test and hand-over. **Per-tool-call audit: not yet** | Vendor logs | Whatever we build |
| Multi-client fit | One QuickBooks login per Claude user | One connection per client, isolation enforced in DB and code | Vendor-specific | Fully ours |
| Maintenance | None | Pin plus upgrade review (the token code is subtle) | Vendor lock-in and pricing | Highest: we track QBO API changes |

**Note on (a):** Intuit's announcement and its Claude plugin README describe connecting a *QuickBooks
company* by signing in with an Intuit account, and say nothing about sandboxes. Intuit's sandbox docs say
sandbox companies are used only with an app's **Development** keys, while Production keys are for live
companies. A production connector therefore shouldn't reach a developer sandbox. I couldn't test this:
there is no QuickBooks connector in this environment. It would also mean real-company data flowing through
a hosted connector, which the brief rules out.

## 2. Decision and trade-offs

**Why (b):**
- It is Intuit's own code and auditable. I read the token handling line by line (DECISIONS_LOG Phase 1).
- It works with the sandbox, and read-only is enforced by **not registering** the write tools, not by
  hoping the model behaves.
- The Console adds what a firm needs and the server lacks: OAuth with `state` checking, encryption at
  rest, an audit trail, and client isolation.

**Rejected:**
- (a): no sandbox; writes by design; credentials outside our control.
- (c): adds a data processor for client financial data, and read-only is not ours to enforce.
- (d): reimplementing 71 well-tested read tools is unjustified for this scope. It becomes the right
  answer if per-call auditing or remote hosting outgrows what upstream offers (§4).

**Claims I checked rather than repeated:**
- **Tool count:** the README says 145. The code registers **142**, and **71** when the three restriction
  flags are on.
- **Test count:** the README says 396 tests. Actually **639**, all passing.
- **Transport:** stdio only. Upstream calls it "a local MCP server … runs as a stdio subprocess". That
  fits one laptop. It is **not** a team-hosting architecture on its own.
- **Rotation is real:** the server persists rotated refresh tokens to its own file and re-reads that file
  on `invalid_grant` (built for sibling *server* processes, not for a second refresher like Django).

**Honest weaknesses:**
- **Read-only is client-side.** The Intuit accounting scope itself allows writes. There is no read-only
  scope.
- **The server's sandbox fallback.** On a dead token in sandbox it launches an interactive OAuth on
  port 8000. Our setup makes that fail safely, because its callback URI isn't registered and Django holds
  the port.
- **Errors aren't flagged.** Upstream returns errors as text without `isError`.
- **`search_accounts` count fails** with HTTP 400 (upstream).
- **Large reports.** A 12-month by-month P&L is about 21k tokens, close to Claude Code's 25k MCP output cap.
- **Dependency advisories.** 8 vulnerable runtime packages were reviewed. Only axios is both high-severity
  and actually used, and it is patched (with a step that must be repeated after `npm ci`). The other seven
  were left unpatched after a reachability analysis (D-04).

## 3. Credential handling, end to end

- **OAuth.**
  - The Console sends the user to Intuit with only the `com.intuit.quickbooks.accounting` scope (least
    privilege) and a 256-bit `state` tied to the session, user and client.
  - `state` is single-use (popped on first callback), compared in constant time, and expires in 10 minutes.
  - The OAuth code is exchanged server-side.
  - The company is then checked on the **sandbox** API host. If it doesn't answer there, the grant is
    revoked and nothing is stored.
- **At rest.** Refresh and access tokens are stored only as **Fernet** ciphertext (AES-128-CBC plus
  HMAC; tampering is detected).
  - The **Fernet key** lives in `connection/.secrets/backend.env`, which is git-ignored, never in the DB,
    and never printed.
  - A stolen `db.sqlite3` alone reveals nothing.
  - Rotating the key means: disconnect all connections, generate a new key, reconnect. An online
    re-encryption command is a next step.
- **File permissions.** All secret material lives in `connection/.secrets/`.
  - On Windows that folder carries an **inheritable owner-only ACL**. This matters because the server
    rewrites its token file with temp-file-plus-rename, and a renamed file takes its directory's
    permissions. I tested this: the same write in an ordinary folder came out readable by every local user.
  - On POSIX the equivalent is `chmod 700`/`600`.
  - `python connection/scripts/init_secrets.py --check` verifies the permissions.
- **Git.**
  - `.gitignore` covers every real `.env`, `*.sqlite3`, `.secrets/` and `evidence/raw/`.
  - A versioned **pre-commit hook** runs `connection/scripts/secret_scan`. It looks for Intuit token and
    client-ID shapes, JWT/JWE tokens, Fernet keys and ciphertext, and credential assignments, and reports
    only `file:line` with a fingerprint, never the value. It has 13 tests, all using generated fakes.
  - Committed docs and evidence were also checked against the actual secret values: clean.
- **Sandbox-only guard, three layers.**
  1. Startup fails unless `QUICKBOOKS_ENVIRONMENT` is exactly `sandbox`.
  2. Every API URL must be `https://sandbox-quickbooks.api.intuit.com`, checked before any network I/O.
  3. Post-connect verification on that host.

  The MCP launcher repeats the check: the server itself treats anything except exactly `sandbox`,
  including `Sandbox`, as production.
- **Rotation and concurrency.** Intuit rotates refresh-token values (about every 24–26 h per Intuit; no
  rotation observed across 9 refreshes in two hours). There is a rolling ~100-day expiry (observed:
  101 days) and a 5-year maximum.
  - **Exactly one owner refreshes each connection.** `export_mcp_env` hands ownership to the MCP server;
    `sync_mcp_tokens` takes it back (refused while a server process is running) and imports any rotated
    token, encrypted.
  - Inside Django, refreshes are serialised with a lock and a re-check.
- **Revocation and disconnect.** **Disconnect** revokes the grant at Intuit, using the newest token,
  which may be in the MCP store. It then always wipes local tokens, and audits whether the revoke succeeded.
- **If a token leaks:**
  1. **Revoke now.** Disconnect in the Console. If the Console is unavailable, disconnect the app inside
     the QuickBooks company.
  2. **Rotate.** If the client secret leaked, regenerate it in the Intuit portal and update `backend.env`.
     If the Fernet key or DB leaked, disconnect every client, issue a new key, and reconnect.
  3. **Contain.** Exit Claude sessions, wipe the token store, and check the audit log and the Intuit app's
     connections for activity you don't recognise.
  4. **If it reached Git:** treat it as compromised even after the history is rewritten.
  5. Record the incident in `DECISIONS_LOG.md`.

## 4. Team hosting (what I would build next)

```
 Staff (SSO) ──► Claude Code / claude.ai ──Streamable HTTP + OAuth/SSO──┐
                                                                        ▼
                    ┌────────────── MCP gateway (authN, client authZ, per-tool-call audit) ─────────────┐
                    │  routes by authorised client → one QBO MCP instance per client (read-only flags)   │
                    └───────┬───────────────────────────────────────┬──────────────────────────────────┘
                            ▼                                       ▼
            QBO MCP (client A, container)            QBO MCP (client B, container)   ← official server behind a
            token from broker, no refresh rights     token from broker               stdio↔HTTP adapter (or fork)
                            │                                       │
                            └──────────────► Token broker (Django) ◄┘  sole refresh owner per connection
                                              │ PostgreSQL (encrypted tokens, audit)   │ Secrets Manager + KMS
                                              ▼                                        ▼   (client secret, Fernet/KMS key)
                                   Intuit OAuth + sandbox-quickbooks.api.intuit.com
 Connection Console (React) ──► Django (Cloud Run / ECS, private network, SSO, WAF) ──► same broker
```

- **Run it as containers** (Cloud Run or ECS) on a private network.
- **Transport:** Claude reaches MCP over **Streamable HTTP** behind an authenticating gateway (SSO or
  OAuth). The official server is stdio-only, so put it behind a stdio-to-HTTP adapter, or fork it.
- **One instance per client:** upstream already supports an isolated `QUICKBOOKS_TOKEN_STORE_PATH` per
  tenant.
- **Secrets:** the client secret and keys go in **Secrets Manager / Secret Manager + KMS**, not `.env`
  files. Tokens and audit data go in **PostgreSQL**, which also gives real row locks for the
  single-owner rule.
- **One refresh owner per connection.** In production I'd make the broker the *only* refresher and have
  servers fetch short-lived access tokens. That needs a small upstream change: today the server cannot
  accept an access token and always refreshes itself (verified). Without the change, keep today's
  check-out lease with exactly one instance per connection.
- **Audit every tool call at the gateway:** user, client, tool, parameters, result size and status,
  shipped to central logging with alerts.
- **Read-only by default.** Any write tool would need an explicit, per-client, reviewed policy.
- **Authorization:** the user-to-client membership check happens at the gateway *and* the broker.
- **Network and monitoring:** egress allow-list (Intuit hosts only), dependency scanning in CI
  (`npm audit`, gitleaks), and token-expiry monitoring (alert 14 days before expiry).

## 5. Multi-client isolation

| Rule | How it is enforced |
|---|---|
| **One connection per client** | `QBOConnection` is one-to-one with `Client` |
| **One active client per company** | A conditional unique constraint on `realm_id`, plus explicit checks. A second client trying to connect a company already in use gets `realm_in_use` |
| **Authorised access only** | Every endpoint resolves the client through the user's memberships. Other clients return 404. The **realm ID is always read from the stored connection, never taken from the request** (tested by sending client B's realm to client A's endpoint) |
| **Tokens per client, owner per connection** | Tokens are stored per connection, with one refresh owner each. The local MCP store holds **one** client at a time: exporting a second is refused, and check-in refuses a store whose realm doesn't match |
| **Tested** | A/B tests cover list, test, disconnect, connect and audit |

A Claude session is therefore bound to exactly one company. The **local demo is not production-ready**:
single SQLite file, `runserver`, session login without SSO or roles, no per-tool-call audit, one laptop.

## 6. Status and next steps

| | |
|---|---|
| **Works and tested live** | OAuth connect; encrypted storage; Test connection (CompanyInfo + P&L); check-out to MCP; `.mcp.json` registration (✔ Connected after user approval); 71 read tools; write tools absent and rejected by name; Claude answers grounded in tool output (3 runs); smoke test 11/11 |
| **Tested with mocks only** | Refresh-token rotation import on check-in; `invalid_grant` handling; revoke failure; non-sandbox company rejection |
| **Partially done** | Per-tool-call audit (Claude-side transcripts only); Fernet key rotation (manual procedure); POSIX permissions (code path written, tested only on Windows) |
| **Not observed yet** | A live refresh-token rotation (needs more than 24 h); upstream's behaviour at the 5-year limit |
| **Before production** | Everything in §4, plus a fork or patched dependency lockfile for the MCP server, CI secret scanning, a project `CLAUDE.md` stating read-only is policy, and a pen test of the Console |

**Sources:**
- [intuit/quickbooks-online-mcp-server](https://github.com/intuit/quickbooks-online-mcp-server) (README and source @ `31a1dd5`)
- [Intuit: QuickBooks expands into Claude and ChatGPT (2026-07-28)](https://www.intuit.com/blog/news-social/quickbooks-expands-into-claude-and-chatgpt-with-new-sales-invoicing-payroll-and-lending-features/)
- [intuit/quickbooks-claude-plugin](https://github.com/intuit/quickbooks-claude-plugin)
- [Intuit Sandbox FAQ](https://developer.intuit.com/app/developer/qbo/docs/develop/sandboxes/sandbox-faqs)
- [Intuit: Handling OAuth token expiration](https://help.developer.intuit.com/s/article/Handling-OAuth-token-expiration)
- [Intuit: Important changes to refresh token policy (2025-11-12)](https://blogs.intuit.com/2025/11/12/important-changes-to-refresh-token-policy)
- Intuit OpenID discovery documents (`developer.api.intuit.com/.well-known/openid_sandbox_configuration`)
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- [CData QuickBooks Online MCP server](https://mcpservers.org/servers/CDataSoftware/quickbooks-online-mcp-server-by-cdata)
- [Pipedream QuickBooks MCP](https://mcp.pipedream.com/app/quickbooks)
- [Composio QuickBooks toolkit](https://composio.dev/toolkits/quickbooks/framework/codex)
