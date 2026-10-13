# Decisions log: Task 1 (QuickBooks Online ↔ Claude)

**Short version:** the 10 most important decisions, on one page, are in [DECISIONS_SUMMARY.md](DECISIONS_SUMMARY.md).

Running log. Each entry records the choice, the alternative(s), why, and how it was verified.
"Verified" means checked against the pinned source (`31a1dd5`) or by running something,
never just the upstream README.

---

## Phase 1: Scaffold and security baseline (2026-10-12)

### What the official server actually does (source inspection, `31a1dd5`)

Recorded first because most later decisions depend on it.

| Question | Finding | Where |
|---|---|---|
| Required env vars | `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET` (hard-required at module load); `QUICKBOOKS_REFRESH_TOKEN`, `QUICKBOOKS_REALM_ID` (needed for calls); `QUICKBOOKS_ENVIRONMENT` (default `sandbox`); `QUICKBOOKS_REDIRECT_URI` (default `http://localhost:8000/callback`) | `src/clients/quickbooks-client.ts:52-63` |
| Optional env vars | `QUICKBOOKS_TOKEN_STORE_PATH` (absolute only, must be in the *host process* env); `QUICKBOOKS_DISABLE_WRITE/UPDATE/DELETE`; `QBO_PDF_OUTPUT_DIR` (enables disk writes from `get_invoice_pdf`; we leave it unset) | `quickbooks-client.ts:28-35`, `register-tool.ts`, `tools/get-invoice-pdf.tool.ts` |
| Where `.env` is loaded from | `dist/clients/../../.env` (package root, *not* CWD), or `QUICKBOOKS_TOKEN_STORE_PATH` | `quickbooks-client.ts:34-35` |
| `.env` precedence | `dotenv.config({ override: true })`: **values in the file beat the host env** (`.mcp.json` `env`). A key absent from the file falls back to the host env | `quickbooks-client.ts:41` |
| `npm run auth` | `node dist/auth-server.js` → `authenticate()` → binds **port 8000** on `::`, opens a browser, validates a random `state`, exchanges the code once (replay-guarded), writes `QUICKBOOKS_REFRESH_TOKEN` + `QUICKBOOKS_REALM_ID` into the token store | `auth-server.ts`, `quickbooks-client.ts:249-422` |
| Access-token refresh | No way to pass an access token in. On the first tool call (and whenever <5 min remains) the server calls Intuit's refresh grant itself. Expiry comes from `expires_in` (fallback 3600 s) | `quickbooks-client.ts:117-120, 495-593` |
| Refresh-token rotation | If Intuit returns a new refresh token, the server **writes it back to the token store** (temp file + rename, `mode 0o600`). If its own token is rejected (400/401/`invalid_grant`), it re-reads the store once and retries, to tolerate a *sibling server process* that rotated it | `quickbooks-client.ts:509-561, 424-485` |
| Dead refresh token in sandbox | Falls back to the **interactive OAuth flow** (port 8000 + browser) from inside a stdio subprocess. In production it throws instead | `quickbooks-client.ts:625-640` |
| Missing credentials | The module installs a global `uncaughtException` handler *before* the credential check, so the startup error is logged and **swallowed**: the process lingers with **zero tools** instead of exiting. Verified by running it against the empty placeholder store | `quickbooks-client.ts:45-63`; run 2026-10-12 |
| Sandbox vs production | `useSandbox = (QUICKBOOKS_ENVIRONMENT === 'sandbox')`, exact match. Any other string, including `Sandbox`, means **production base URL** | `quickbooks-client.ts:651` |
| Restriction flags | Exist. A tool is skipped at **registration** if its name starts with `create_`/`update_`/`delete_` (or hyphen variants) and the matching flag `=== "true"` (exact, lowercase; `TRUE`/`1` do nothing). Names starting `get_`/`search_`/`read_` are never suppressed | `src/helpers/register-tool.ts` |
| Tool count | **142 registered** (README badge says 145: three `RegisterTool` lines are commented out). By name: 40 `get`, 29 `search`, 2 `read` (71 read) / 25 `create`, 26 `update`, 20 `delete` (71 mutating). README's `get_aged_receivables_detail` does not exist | `src/index.ts`, `src/tools/*.ts` |
| Do "read" tools mutate? | Read-category handlers call only `get*`, `find*`, `report*` on node-quickbooks (HTTP GET). `get_invoice_pdf` can write to *local disk* only if `QBO_PDF_OUTPUT_DIR` is set | `src/handlers/{get,search,read}-*.ts` |
| OAuth scope | `com.intuit.quickbooks.accounting` (`OAuthClient.scopes.Accounting`). Intuit has no read-only accounting scope, so **the token itself can write**; read-only is enforced only by which tools exist | `quickbooks-client.ts:398` |
| Transport | stdio only. No HTTP transport in this server | `src/index.ts` |

### D-01: Use the official Intuit MCP server (stdio, read-only)
- **Choice:** `intuit/quickbooks-online-mcp-server`, run locally over stdio with all three restriction flags `true`.
- **Alternatives:** native Claude connector, third-party hosted MCP/sync, custom MCP on the QBO API.
  The full comparison is in `CONNECTION.md` (Phase 6).
- **Why (so far):** first-party, MIT-licensed, auditable (we read the token code above), 639 upstream unit
  tests pass, sandbox supported, restriction flags verified in source.
- **Known weaknesses:** read-only is client-side only (see scope row above); stdio is a local-process
  design, not team hosting; upstream docs overstate tool and test counts.

### D-02: Pin with a Git submodule, not a git-ignored clone
- **Choice:** submodule at `connection/quickbooks-online-mcp-server`, gitlink `31a1dd5`.
- **Alternative:** git-ignored clone plus a SHA in `SERVER_VERSION.md`.
- **Why:** with a submodule, Git records the pin in the parent tree. A reviewer can check it with
  `git ls-tree`, and `git submodule status` shows drift (`+`). With an ignored clone the pin is only a
  sentence in a doc. The usual worry with a submodule is committing build output or `.env` by
  accident, but the inner repo's own `.gitignore` already covers `node_modules`, `dist` and `.env`, and
  the parent never commits the inner working tree.
- **Cost:** teammates must run `git submodule update --init` (in the Quick Start).

### D-03: `npm ci` (lockfile-exact), after reviewing install scripts
- Inspected `package-lock.json` for `hasInstallScript` before installing: only `fsevents` (macOS, skipped)
  and `unrs-resolver` (dev dependency of Jest). Both are well-known, so I proceeded.
- `npm ci` rather than `npm install` so the lockfile is not rewritten and the build matches the pin.

### D-04: Runtime dependency advisories: verified reachability; axios patched, the rest left by decision
- **Status (2026-10-12):** analysis complete. **axios 1.19.0 → 1.20.0 has been applied to this repo's
  `node_modules`** and verified, not just evaluated (see "Applied fix" below). The submodule pin
  (`31a1dd5`), its `package.json` and its `package-lock.json` are unchanged. The other 7 vulnerable
  packages are deliberately left unpatched ("Left unpatched by decision").
- **Required after every `npm ci`:** the fix lives only in `node_modules`, so it must be re-applied after
  any `npm ci`/clean install. It is a required post-clone step in `SERVER_VERSION.md` and the README
  Quick Start.
- **Scope:** `npm audit --omit=dev` at `31a1dd5` reports **8 vulnerable packages** (npm's
  "8 vulnerabilities": 1 critical, 2 high, 5 moderate) carrying **20 distinct GHSA advisories**. My
  Phase 1 summary called these "8 advisories", which was wrong. The preconditions below come from each
  advisory's own text (`api.github.com/advisories/<GHSA>`), not from its title.

#### Three separate questions
- **Installed:** present in `node_modules`. This is all `npm audit` checks.
- **Loaded:** the module is actually evaluated inside the running server process.
- **Exploitable:** the vulnerable function runs, under the advisory's stated preconditions, on input an
  attacker can influence.

#### Evidence and method
1. **Dependency paths:** `npm ls --omit=dev --all`.
2. **Startup trace:** `dist/index.js` run under a `module.registerHooks()` resolve hook, which sees both
   ESM `import` and CJS `require`. The token store was a scratch file holding obvious placeholder values,
   so the module-level credential check passes; no real credentials were used.
3. **Request-time trace:** a harness spoke MCP JSON-RPC over stdio (`initialize`, `tools/list`, and a
   `tools/call` with schema-invalid arguments). Inside the server process, outbound `net`/`tls`
   connections and `http.Server.listen` were blocked, and call counters were wrapped around `fast-uri`
   and `decode-uri-component`. Results:
   - modules loaded after startup: **0**
   - outbound connection attempts: **0**; `listen()` calls: **0**
   - `decode-uri-component` calls: **0**
   - `fast-uri` calls: **2**, both made while ajv starts up, with a *constant* input:
     `parse("http://json-schema.org/draft-07/schema")` and `serialize(<that object>)`
   - SDK `client/*`, `*auth*` or Express files loaded: **none**
   - The invalid call was rejected by input validation (`-32602`) before any handler ran.
4. **Lazy-load check (static):**
   - There is no dynamic `import()` anywhere in the server's `dist/`.
   - The only "express" match in `dist/` is the word "expressed" in a tool description
     (`dist/tools/create-payment.tool.js`).
   - The SDK files that load contain no `import()`/`require()` of Express.
   - In `intuit-oauth`/`node-quickbooks`, the only function-scoped `require` is
     `rsa-pem-from-mod-exp`, used in ID-token validation; it is not flagged by the audit. The other
     matches are module-level declarations.
5. **axios configuration (static):** `intuit-oauth` uses `axios.create({validateStatus})` and
   `axios(request)`; `node-quickbooks` uses `axios(opts)`/`axios.post`. Neither sets `adapter`,
   `httpVersion`/HTTP/2 options, `proxy` or `maxRedirects`. axios's default adapter order is
   `['xhr','http','fetch']`, so Node uses the **http** adapter. All request URLs are fixed Intuit HTTPS
   endpoints plus entity paths. No `HTTP(S)_PROXY`/`NO_PROXY` variables are set here.

#### Per package
Versions are as audited at the pin, i.e. what the lockfile installs. The axios row records the state
*before* the fix.

| Package (installed) | Sev. | GHSA | Dependency path | Loaded | Exploitable here | Fixed in | Fits declared range? |
|---|---|---|---|---|---|---|---|
| `proxy-addr` 2.0.7 | **critical** | jqcg-44mw-7w3h | sdk → express 5.2.1 → proxy-addr | **No** | **No.** Requires Express `trust proxy` with a mis-specified IPv4-mapped or zero-prefix IPv6 subnet. Express is never loaded (stdio server) | 2.0.8 | Yes (`^2.0.7`) |
| `@modelcontextprotocol/sdk` 1.30.0 | **high** | 6qxp-vccf-f47h | direct | Yes, server files only | **No.** Affects apps using the SDK's *OAuth client* over HTTP (`authProvider` on a transport). This process is an MCP *server* and never loads `client/*` | 1.31.0 | Yes (`^1.26.0`) |
| `axios` 1.19.0 | **high** | 12 (7 high, 5 moderate), next table | intuit-oauth → axios; node-quickbooks → axios (deduped) | **Yes** | **The package is exercised** on every token refresh and every QuickBooks API call. **No high-severity advisory's preconditions hold** in this configuration | 1.20.0, **applied** | Yes (`^1.18.1`, `^1.13.2`) |
| `ip-address` 10.4.0 | moderate | rpw4-54j3-4h4q, 2vr4-cq9g-pvrc, j6r3-76f7-8jcv, h3mg-xc3c-68pw | sdk → express-rate-limit → ip-address | **No** | No | 10.7.1+ | Yes (`^10.2.0`) |
| `fast-uri` 3.1.7 | moderate | hrr3-gc8f-f4qj | sdk → ajv 8.20.0 → fast-uri | **Yes** | **No.** The bug makes host comparison inconsistent for attacker-supplied scheme-relative URIs. The only call is the constant draft-07 meta-schema URL at ajv start-up. ajv validates user data only for elicitation, which this server never sends | 3.1.8 | Yes (`^3.0.1`) |
| `decode-uri-component` 0.2.2 (also flags `query-string` 6.14.1 and `intuit-oauth` 4.2.5) | moderate | vcc3-ghjq-m6fr | intuit-oauth → query-string → decode-uri-component | **Yes** | **No, in our design.** It is reached only through `createToken(callbackUrl)` in the server's *interactive OAuth flow*, which we never run (D-06/D-07). Upstream also rejects a bad `state` before parsing. 0 calls observed | 0.5.0 | **No** (`query-string` pins `^0.2.0`); npm reports "no fix available" |

#### axios advisories against the observed configuration

| GHSA | Sev. | Precondition (from the advisory) | Holds here? |
|---|---|---|---|
| c29m-xwm3-cm6r: ReDoS in `fromDataURI` | high | untrusted URL strings passed to axios, `data:` URLs not rejected | No. URLs are fixed Intuit HTTPS endpoints |
| mghh-pgcx-3jjj: ReDoS in `shouldBypassProxy` | high | env proxy vars with `NO_PROXY`, plus a redirect from an attacker-controlled server | No proxy env; requests go only to Intuit |
| x97p-jq2g-jp4f: form-serialisation prototype-pollution gadget | high | `Object.prototype` already polluted elsewhere in the process | No pollution source identified (see Limitations) |
| m8m8-qj5v-23w3: `createConnection` prototype-pollution gadget | high | same as above | Same as above |
| 3pq3-5fj3-cg6v: HTTP/2 skips lookup/proxy controls | high | `httpVersion: 2` and user-influenced destinations | No. HTTP/1.1 only; `http2` is imported by the bundle but that path is unused |
| 542g-h47m-68v8: HTTP/2 session error crashes the process | high | `httpVersion: 2` | No |
| r4gj-5m52-g5wh: `maxRedirects: 0` ignored | high | fetch adapter, and relying on `maxRedirects: 0` | No. http adapter; option not used |
| vh66-26gq-q6x8, 4hqw-qxg8-jxx2 | moderate | fetch adapter | No |
| 9fr6-4gfg-395g, j8rh-479h-cp32 | moderate | existing prototype pollution | None identified |
| 44g4-m2mj-wpvx | moderate | proxy configured with CIDR `NO_PROXY` | No |

#### Verdict
- **Critical, or high and loaded:** only `axios` is both high-severity and loaded/exercised. None of its
  advisories was exploitable in this configuration. Its residual risk was the two prototype-pollution
  gadget advisories, which would matter only if a pollution bug existed elsewhere in the process. All
  12 axios advisories are now closed by the applied fix, as long as the post-`npm ci` step is followed.
- **Critical `proxy-addr` and high `@modelcontextprotocol/sdk`:** installed but not reachable.
  `proxy-addr` is never loaded; the SDK's vulnerable client code is never loaded.

#### Limitations (what this analysis does not prove)
- The **refresh and QuickBooks API call paths were not traced at runtime**, because that needs real
  credentials and network access, and with a placeholder token the server's sandbox fallback would try
  interactive OAuth. Those paths were assessed statically (point 5). The Phase 5 sandbox smoke test will
  exercise them.
- The prototype-pollution conclusion rests on MCP input being `JSON.parse`d (which creates `__proto__`
  as an own key, not a pollution) and zod-validated. I did not exhaustively audit every transitive
  dependency for pollution sources.
- The verdicts are tied to **this configuration**: stdio transport, no proxy env, no
  `QBO_PDF_OUTPUT_DIR`, interactive OAuth unused. A team deployment using the SDK's **Streamable HTTP
  transport would load Express** and make `proxy-addr`, `ip-address` and `express-rate-limit` relevant.
  Re-run this analysis then.
- The trace used a store **without** the restriction flags (`tools/list` returned all 142 tools). That
  does not affect module reachability. Read-only enforcement is verified separately in Phase 4.

#### Applied fix: axios 1.19.0 → 1.20.0 (applied and verified in this repo, 2026-10-12)
- **Why only axios:** it is the only high/critical package that is loaded and exercised. 1.20.0
  (published 2026-08-26) closes all 12 axios advisories, is a minor bump, and satisfies both
  dependents' declared ranges.
- **How:** it lives in `node_modules` only, so the pin stays faithful:

  ```bash
  cd connection/quickbooks-online-mcp-server
  npm ci                                                  # exact upstream lockfile
  npm install --no-save --ignore-scripts axios@1.20.0     # node_modules only; package*.json untouched
  npm ls axios                                            # every path must show axios@1.20.0
  npm run build
  ```
- **Verification in this repo** (all run after applying):

  | Check | Result |
  |---|---|
  | `npm ls axios --all` | `intuit-oauth → axios@1.20.0`; `node-quickbooks → axios@1.20.0 deduped`; no `invalid` |
  | Runtime resolution from `intuit-oauth` | `axios@1.20.0` |
  | Every installed package compared with `package-lock.json` (628 checked) | exactly one difference: `node_modules/axios` lockfile 1.19.0 → installed 1.20.0. Nothing else moved, nothing missing |
  | Submodule `git rev-parse` / `git status --porcelain` | `31a1dd5` / empty, so the pin and lockfile are untouched |
  | `npm run build` | exit 0 |
  | `npm test` (upstream suite) | **639/639 passed, 35/35 suites** |
  | Stdio run (`initialize`, `tools/list`, invalid `tools/call`, network blocked) | starts normally, 142 tools listed, invalid call rejected by validation, 0 connection attempts |

  (Before touching this repo, the same fix was trial-run in a throwaway clone with the same results.)
- **Verify with `npm ls axios`, not `npm audit`.** `npm audit` reads the lockfile, so it **still
  reports axios 1.19.0** (confirmed after applying). That entry is expected and is not a regression.
- **Must be repeated after any `npm ci`** or fresh clone. `npm ci` reinstalls exactly what the lockfile
  says and silently reverts the fix. It is therefore a required post-clone step in `SERVER_VERSION.md`
  and the README Task 1 Quick Start, not a one-off.
- **Remaining check:** upstream's tests mock HTTP, so they don't exercise axios's network layer. The
  Phase 5 sandbox smoke test is the first real refresh and API call through 1.20.0.

#### Left unpatched by decision (re-evaluate if the configuration changes)

| Package | Sev. | Why not patched | Revisit when |
|---|---|---|---|
| `proxy-addr` 2.0.7 | critical | never loaded (Express unused) | the server is deployed over HTTP (Streamable HTTP via Express) |
| `@modelcontextprotocol/sdk` 1.30.0 | high | vulnerable OAuth-*client* code never loaded; a bump would also change the server's own MCP runtime | MCP client/auth features are used, or the pin moves |
| `ip-address` 10.4.0 | moderate | never loaded | HTTP deployment (express-rate-limit) |
| `fast-uri` 3.1.7 | moderate | loaded, but only ever given the constant draft-07 meta-schema URL | the server starts sending elicitation requests |
| `decode-uri-component` 0.2.2 (`query-string`, `intuit-oauth`) | moderate | reached only by the interactive OAuth flow we never run; no fix fits `query-string`'s `^0.2.0` range | our design starts using the server's own OAuth flow |

The SDK, `proxy-addr`, `ip-address` and `fast-uri` fixes are semver-compatible. They belong in a reviewed
lockfile update in an owned fork, not in more `--no-save` overrides.

#### Before team use
Build from an owned fork or container image whose **lockfile** carries patched versions (a real lockfile
bump or npm `overrides`), so that `npm audit` reflects what actually runs. Gate CI on
`npm audit --omit=dev --audit-level=high`, with a reviewed allow-list for advisories proven unreachable.
Re-run this reachability analysis whenever the pin or the transport changes.

### D-05: All secret material in one owner-only directory, `connection/.secrets/`
- **Choice:** `backend.env`, `mcp-server.env` (MCP token store) and `db.sqlite3` all live in
  `connection/.secrets/`, which is git-ignored and **directory-level** locked:
  - Windows: `icacls /inheritance:r /grant:r <owner-SID>:(OI)(CI)F`, a single inheritable owner ACE
  - POSIX: `chmod 700` on the directory and `600` on its files.
  Script: `connection/scripts/init_secrets.py` (idempotent; `--check` verifies).
- **Alternative:** `backend/.env` and the server's own `.env` with per-file `chmod 600`.
- **Why (verified):**
  1. `E:\RE-Finance` inherits `Authenticated Users: Modify` and `Users: Read`, so on this laptop any
     local account could read a normal file.
  2. `chmod 600` has no effect on NTFS, and Node's `writeFileSync(..., {mode: 0o600})` is ignored on Windows.
  3. The MCP server rotates tokens with **temp file + rename**. A renamed file keeps the ACL of the
     *temp* file, which is inherited from its directory. Tested: the same Node write produced an
     owner-only file inside `.secrets/` but `Users:(RX)` in an ordinary folder. A per-file ACL would be
     lost on the first rotation; a directory ACL is not.
- **Unix vs Windows difference:** Unix mode bits are three fixed classes (owner/group/other) checked on
  the file. Windows uses an ACL with any number of principals, inherited from the parent by default.
  "Owner-only" therefore means removing inheritance and leaving a single ACE. Administrators can still
  take ownership on both systems; this protects against other non-admin users and casual exposure, not a
  local admin.

### D-06: Humans enter the Intuit client ID and secret in exactly one file
- **Choice:** `connection/.secrets/backend.env` only. The MCP token store is *generated* from the
  encrypted DB by `manage.py export_mcp_env` (Phase 2/4), and `init_secrets.py` writes it now as an empty
  placeholder (sandbox, all restriction flags `true`, no credentials).
- **Alternative:** the user also pastes credentials into the server's `.env` and runs `npm run auth`.
- **Why:** one entry point means one copy to rotate. The MCP server's `npm run auth` would create a
  *second* OAuth grant and a *second* refresh-token owner outside Django's audit log, so we don't use it.

### D-07: OAuth redirect URI is Django's; the server's built-in callback is deliberately *not* registered
- **Choice:** register only `http://localhost:8000/api/qbo/callback` on the Intuit app.
- **Why:** Django is the only component that performs the OAuth code exchange (with session-bound
  `state`, encryption at rest and an audit log). Leaving the server's `http://localhost:8000/callback`
  *unregistered* means its sandbox interactive fallback (see table) cannot complete even if triggered:
  Intuit rejects the unregistered redirect. If Django is running it also holds port 8000, so the
  fallback's listener fails with `EADDRINUSE`.

### D-08: Token ownership: a check-out/check-in *lease* (design; implemented in Phases 2 and 4)
- **Constraint from the source:** the server always refreshes on its own and writes rotations back to
  its store. It cannot be fed an access token. So "Django is the only refresher and MCP only uses access
  tokens" is impossible without patching upstream.
- **Rejected:** Django and MCP both refreshing the same token. Intuit invalidates the previous refresh
  token on rotation, and two refreshers with no shared lock can strand each other. The server's
  "re-read the file on 400" retry only helps sibling *server* processes sharing one file, not Django.
- **Rejected:** the prompt's `export_mcp_env` / `sync_mcp_tokens` pair used *while both stay live*. That
  is still two owners.
- **Chosen:** exactly one owner per connection at any time, recorded in the DB (`token_owner`):
  - `export_mcp_env --client X` = **check-out**: Django refreshes once (to validate the grant and get a
    fresh token), writes the token store with owner-only permissions, sets `token_owner=mcp`, and audits
    it. While checked out, Django **refuses to refresh** that connection.
  - `sync_mcp_tokens --client X` = **check-in**: reads the possibly rotated token back, re-encrypts it
    into the DB, wipes the store, sets `token_owner=django`. It requires the MCP server to be stopped
    (best-effort process check plus an explicit override flag), because a running server still holds
    the old token in memory.
  - Only one client can be checked out to the single local store at a time. This keeps the local MCP
    server bound to exactly one realm (multi-client isolation).
- Token lifetime figures (access ~60 min, refresh rolling ~100 days, rotation cadence) will be verified
  against Intuit's current docs in Phase 4 before they are written down here as facts.

### D-09: Read-only = all three restriction flags, set in two places, plus a pre-flight launcher (Phase 4)
- The token store sets `QUICKBOOKS_DISABLE_{WRITE,UPDATE,DELETE}=true`. Because of `override: true`, the
  file wins over `.mcp.json`. `.mcp.json` sets them too as a fallback in case the file lacks the keys.
- Planned launcher `connection/scripts/mcp_launch.mjs` (referenced from `.mcp.json` by relative path):
  sets `QUICKBOOKS_TOKEN_STORE_PATH` to the absolute path (`.mcp.json` should not hold machine-specific
  absolute paths), and **refuses to start** unless the store has credentials, `QUICKBOOKS_ENVIRONMENT`
  is exactly `sandbox`, and all three flags are exactly `true`. It then imports `dist/index.js` in-process.
  This turns the "lingers with zero tools" failure and the case-sensitive `sandbox` check into clear,
  non-zero exits.
- **Honest limit:** this is defense in depth on the client side. The OAuth grant still has write scope
  at Intuit.

### D-10: Small custom secret scanner + versioned pre-commit hook (instead of gitleaks/detect-secrets)
- **Choice:** `connection/scripts/secret_scan` (Python stdlib only) and `.githooks/pre-commit`, enabled
  per clone with `git config core.hooksPath .githooks`.
- **Alternatives:** `gitleaks` (a Go binary install), `detect-secrets` (a pip dependency plus baseline file).
- **Why:** no extra install for reviewers; rules specific to this project (Intuit refresh-token and
  client-ID shapes, JWT/JWE access tokens, **Fernet ciphertext `gAAAAA…`**, Fernet keys, Django keys,
  credential assignments with real-looking values); blocks forbidden *files* (`.env`, `*.sqlite3`,
  `.secrets/`, `evidence/raw/`) by path; **reports `file:line`, the rule and a `len`/`sha256[:8]`
  fingerprint, never the value.**
- **Verified:** `test_secret_scan.py`, 11/11 passing. It covers each secret type with runtime-generated
  fakes (no fake literal sits in the source, so the scanner doesn't flag its own test), asserts the value
  never appears in the output, checks placeholders and code references stay clean, and runs an
  end-to-end hook check in a throwaway repo (secret commit blocked, clean commit allowed).
- One false positive was found and fixed: a placeholder inside a Python string literal picked up a
  trailing `\n` escape.
- **Team recommendation:** additionally run gitleaks in CI. A local hook can be bypassed with `--no-verify`.

### D-11: LF line endings enforced (`.gitattributes`)
- Git on this machine converts to CRLF. A CRLF shebang breaks `.githooks/pre-commit` under POSIX shells.

---

## Phase 2: Django backend (2026-10-12)

### Checkpoint 1 follow-up
- The credentials were entered as `KEY = VALUE`, with spaces around `=`. Some `.env` parsers would read
  the space as part of the value, so I normalised the two lines to `KEY=VALUE` in place, which keeps
  the file's ACL. Values were validated by shape only (alphanumeric; ID 50 chars, secret 40 chars) and
  never printed.

### D-12: OAuth with plain `requests`, not Intuit's Python `intuit-oauth` library
- `intuit-oauth` 1.2.7 would add 6 packages (`PyJWT`, `requests-oauthlib`, `oauthlib`, `six`,
  `enum-compat`), two of them Python 2 compatibility shims, for three HTTP calls (code exchange,
  refresh, revoke).
- Endpoints were taken from Intuit's discovery documents, fetched 2026-10-12
  (`developer.api.intuit.com/.well-known/openid_sandbox_configuration` and `openid_configuration`).
  Authorize: `appcenter.intuit.com/connect/oauth2`; token: `oauth.platform.intuit.com/oauth2/v1/tokens/bearer`;
  revoke: `developer.api.intuit.com/v2/oauth2/tokens/revoke`.
- Only the OAuth error *code* is surfaced on failure (`invalid_grant`, `invalid_client`, …), never the
  response body.

### D-13: Sandbox guard has three layers, because the OAuth endpoints can't tell sandbox from production
- **Verified:** the sandbox and production discovery documents list *identical* authorize, token and
  revoke endpoints. "Is this sandbox?" can therefore only be enforced at the accounting API.
  1. **Settings:** startup fails unless `QUICKBOOKS_ENVIRONMENT` is exactly `sandbox`. `Sandbox` is also
     refused, mirroring the official server's exact-match check.
  2. **Host allow-list:** every API URL must be `https://sandbox-quickbooks.api.intuit.com/...`
     (`intuit.assert_sandbox_url`), checked on the final URL *before* any network I/O. The realm ID must
     be all digits, so it can't alter the path.
  3. **Post-connect verification:** after the code exchange, CompanyInfo is fetched on the sandbox host.
     If that fails, the new grant is **revoked** and nothing is stored.
- **Honest limit:** Intuit credentials have no offline marker distinguishing Development keys from
  Production keys. A production company connected with Production keys would fail layer 3, not be
  detected up front.

### D-14: Authentication and authorization for the local demo
- Django session auth with a server-rendered, CSRF-protected login form at `/api/auth/login/`,
  reached through the Vite proxy. DRF uses `SessionAuthentication` only, `IsAuthenticated` by default,
  and the JSON renderer only (no browsable API). Unsafe methods need the CSRF token (tested).
- **Per-client authorization:** `Client.members` (M2M to User). Every view resolves the client through
  `qbo/access.py` (`Client.objects.filter(members=user)`). Another client's slug returns **404**, the
  same as a missing one, so existence isn't disclosed. The realm ID is always read from the stored
  connection and never accepted from a request (tested by passing B's realm to A's endpoint).
- **Not production-ready:** no SSO/MFA, no roles (every member can connect or disconnect), single
  SQLite database, `runserver`, `DEBUG=true`. See `CONNECTION.md` (Phase 6) for the team design.

### D-15: OAuth callback hardening
- `state` is 256-bit random and stored in the server-side session together with the client slug, user
  ID and issue time. It is **popped on first use** (no replay, even after a mismatch), compared in
  constant time, and expires after **10 minutes**. A callback from a different user's session is rejected.
- Redirects back to the SPA carry only a fixed vocabulary of reason codes; Intuit's text is never reflected.
- **One active client per company:** a conditional `UniqueConstraint` on `realm_id` where
  `status != disconnected`, plus explicit checks. A realm connected to client B can't be attached to
  client A, and a client with a connected company must disconnect before connecting a different one.
- Re-authorising a connection that is checked out to the MCP server is refused, since it would create
  a second token owner.

### D-16: Token-lease implementation (the D-08 design, built)
- `QBOConnection.token_owner` is `django` or `mcp`. `tokens.refresh_now()` refuses unless the owner is
  `django`. That is the **only** code path in the backend that calls Intuit's refresh grant.
- **Concurrency in Django:** a per-connection re-entrant lock plus `select_for_update()` (a real row
  lock on PostgreSQL; on SQLite writes are serialised anyway), with a re-check after the lock is taken.
  Two simultaneous `/test` calls cannot both spend one rotating refresh token.
- **`export_mcp_env` (check-out):** under the lock it refreshes once (validates the grant, gets a fresh
  token), writes the token store with temp file + rename in the owner-only dir, sets all three
  restriction flags to `true` and `QUICKBOOKS_ENVIRONMENT=sandbox`, then sets `token_owner=mcp`. It
  refuses if another client is already checked out: one local store, so one realm at a time.
- **While checked out:** Django serves `/test` only from its cached access token (about 60 min after
  check-out). After that it returns 409 with check-in instructions. The encrypted refresh token stays
  in the DB as an escrow copy, used only to revoke on disconnect, never to refresh.
- **`sync_mcp_tokens` (check-in):** refuses while a server process is detected (Windows: `node.exe`
  command lines via CIM; POSIX: `ps`). If detection fails it also refuses unless `--force`. It refuses
  if the store's realm differs from the connection's (isolation), imports a rotated token encrypted,
  wipes the store and sets the owner back to `django`.
- **Bugs found and fixed while building:**
  1. A refresh failure inside the row-lock transaction rolled back the `refresh_required` status and
     its audit row. The failure is now captured, the transaction commits, and the error is raised
     afterwards. A test asserts the status persists.
  2. Check-out re-entered the per-connection lock and would have deadlocked. Switched to `RLock`.

### D-17: Keeping secrets out of logs, error pages and audit rows
- `runserver` logs full request lines, including the callback's `?code=…&state=…&realmId=…`. A logging
  filter (`qbo/logging_filters.py`) redacts those parameters (tested).
- Token-handling functions use `@sensitive_variables`, so Django's DEBUG error page masks their locals.
- `audit.record()` scrubs token-shaped strings from `detail` as a second line of defence. Callers pass
  fixed messages anyway (tested; the mutation test confirms the test catches removal of the scrubber).
- API responses expose `realm_hint` (first 4 characters + "…") and never the full realm ID or any token.

### D-18: Disconnect semantics
- Revoke at Intuit (revoking the refresh token revokes the grant), then **always** wipe the local
  tokens and set `disconnected`, even if the revoke fails. The audit row's `success` mirrors the revoke,
  so a grant that wasn't revoked stands out for manual follow-up.
- If the connection is checked out, the newest token is read from the MCP store (the server may have
  rotated it) and revoked, and the store is wiped. The running server then fails its next refresh.
  Because Django holds port 8000 and the server's own callback URI is not registered (D-07), its
  sandbox interactive-OAuth fallback cannot complete.

### D-19: Backend tests: 63 passing, and checked to fail when safeguards are removed
- `python manage.py test qbo --settings=config.settings_test`: **63 tests, OK**.
- The test settings use ephemeral keys, an in-memory DB and a temp token store, and never read
  `connection/.secrets/`. Intuit and QuickBooks are faked at the `requests` layer, so the real
  refresh, revoke and guard code runs. Fake tokens are random and generated at run time.
- Coverage:
  - Fernet round-trip, tamper and wrong-key detection, and ciphertext-only storage in the DB
  - `state` missing, mismatched, replayed, expired or from another user
  - denied consent and malformed realm
  - success, non-sandbox company (revoked), realm already used by another client
  - A/B isolation across list, test, disconnect, connect and audit, and an ignored request-supplied realm
  - unauthenticated requests and missing CSRF token
  - no tokens, secrets or full realm in responses, audit rows or captured logs
  - log redaction
  - production URLs and malformed realms refused before any I/O; settings refuse `production` and `Sandbox`
  - refresh, rotation, `invalid_grant`, transient errors, and no refresh while checked out
  - disconnect: revoke success, revoke failure, checked-out case
  - `create_client`, `export_mcp_env`, `sync_mcp_tokens` (rotation, running server, unknown process
    state, realm mismatch)
- **Mutation check:** I removed five safeguards one at a time (state comparison, single-owner guard,
  client scoping, sandbox host guard, audit scrubber). Every one made the suite fail.
- **Not covered:**
  - real Intuit behaviour (Phase 4/5)
  - true multi-threaded races (the lock logic is exercised single-threaded)
  - the Windows ACL of the store in tests (the temp dir isn't locked; the real `.secrets/` ACL is
    verified by `init_secrets.py --check`)

---

## Phase 3: React frontend (2026-10-12)

### D-20: Vite's official React **JavaScript** template, with its TypeScript type packages removed
- Scaffolded with `create-vite@9.2.1 --template react` (official, `vitejs/vite`, no runtime
  dependencies). It was generated in a scratch directory first and inspected before being copied in.
- The "JS" template still ships `@types/react` and `@types/react-dom` as devDependencies (for editor
  IntelliSense). Both were removed so there is no TypeScript anywhere. Verified: 0
  `.ts`/`.tsx`/`tsconfig*` files outside `node_modules`, and `npm ls typescript @types/react
  @types/react-dom --all` is empty.
- Kept the template's linter, **Oxlint** (configured in JSON, JS rules only; `npm run lint` exits 0).
  Removed the demo assets and README.
- `npm install --ignore-scripts`: 21 packages, 0 vulnerabilities. The only package with an install
  script is `fsevents` (macOS-only).

### D-21: Same-origin via the Vite proxy; CORS is effectively unused
- `/api` is proxied to `localhost:8000` with `changeOrigin: false`. Django then sees
  `Host: localhost:5173`, which matches the browser's `Origin`, so its CSRF origin check passes without
  loosening. `strictPort` pins 5173, because `FRONTEND_URL` and `CSRF_TRUSTED_ORIGINS` depend on it.
- Only the OAuth **callback** goes to `:8000` directly (the registered redirect URI). Cookies on
  `localhost` are not port-scoped, so the session cookie set through `:5173` comes back on that request.
- `django-cors-headers` is installed (as the brief asked) but only allows `FRONTEND_URL`. It's needed
  only if the UI is served without the proxy.

### D-22: What the browser can and cannot see
- Auth is the **HttpOnly** Django session cookie. The only cookie JS reads is `csrftoken`, a CSRF nonce
  that is not a credential on its own. No `localStorage`/`sessionStorage`, no `VITE_*` variables, no
  secrets in the bundle (`secret_scan` over `src/` and `dist/` is clean), and `sourcemap: false`.
- The API never returns tokens, so the UI can't display them. It shows `realm_hint` (first 4
  characters + "…").
- The password is entered only on Django's own server-rendered login form, never in React.
- OAuth results come back as fixed reason codes, mapped to messages in `src/format.js`. The query
  string is removed from the address bar after it has been read.

### D-23: UI structure: small components, native primitives
- `App.jsx` (session + callback notice) → `ClientList.jsx` → `ClientCard.jsx` (status, token expiry,
  Connect/Test/Disconnect) → `TestResult.jsx` (company + P&L). Also `AuditLog.jsx`, `ConfirmDialog.jsx`
  (native `<dialog>`, so focus trapping and Esc come from the browser), `Notice.jsx`
  (`role=alert`/`status`), `SignIn.jsx` and `Header.jsx`. Data access is in `api.js`, formatting in
  `format.js`.
- Plain CSS with custom properties and a dark-mode palette. Responsive down to 320 px. Visible
  `:focus-visible` outline. Buttons carry client-specific `aria-label`s.
- Every list has loading, empty and error states. P&L sections QuickBooks didn't return are omitted,
  not shown as 0.

### Verified at the end of Phase 3
- `npm run build`: OK (index ~235 kB, ~74 kB gzipped). `npm run lint`: exit 0. Backend tests still 63/63.
- Live, with both servers running:
  - `/api/me/` through the proxy returns `{"authenticated": false, ...}`
  - `/api/clients/` without a session returns 403
  - the login page returns 200
  - `connect` while logged out redirects to the login page with `next`
  - a callback with no state redirects to `?qbo=error&reason=invalid_state`
  - Django's console line for that callback shows `code=[redacted]&realmId=[redacted]`
- **Not yet verified:** real OAuth against Intuit (Checkpoint 2), and visual or browser testing. I have
  no browser in this session, so the UI has been built and linted but not looked at.

---

## Phase 4: Connecting Claude through the official MCP server (2026-10-12)

### Connection stored (after Checkpoint 2)
- Client `abc-inc-sandbox`, member `nithin`, realm `9341…`, status `connected`, environment `sandbox`.
- Both tokens are stored as Fernet ciphertext. The audit trail shows `oauth_start` → `oauth_callback`
  (company verified on the sandbox host) → `test_connection` OK, all by `nithin`.

### D-24: `.mcp.json` points at a pre-flight launcher, not straight at `dist/index.js`
- `.mcp.json` (project scope) runs `node connection/scripts/mcp_launch.mjs`. The path is relative and
  the file holds no secrets: only the command, the argument, and fallback env values for
  `QUICKBOOKS_ENVIRONMENT=sandbox` and the three `DISABLE_*=true` flags. The server's real entry point
  `dist/index.js` (verified in `package.json` `main`/`bin`) is imported by the launcher.
- The launcher refuses to start (exit 1, message on stderr, no values printed) when:
  - the server isn't built;
  - **axios < 1.20.0** (catches a forgotten D-04 step after `npm ci`);
  - the token store is missing or empty (the server itself would linger with zero tools);
  - the realm is malformed;
  - `QUICKBOOKS_ENVIRONMENT` isn't exactly `sandbox`;
  - any `DISABLE_*` flag isn't exactly `true`.

  The flags are checked *in the store file* because the server's `dotenv override:true` makes the file
  win over `.mcp.json`.
- It sets `QUICKBOOKS_TOKEN_STORE_PATH` to the absolute path of `connection/.secrets/mcp-server.env`
  (the server requires an absolute path), unsets `QBO_PDF_OUTPUT_DIR`, and never writes to stdout,
  which is the MCP channel.
- **Tested:** refusal for an empty store, `Sandbox` (wrong case), `DISABLE_WRITE=TRUE`, and a
  malformed realm. Happy path verified by the smoke test.
- **Alternative rejected:** `${VAR}` expansion in `.mcp.json` for the absolute store path. That works
  (documented), but every teammate would have to export a variable before launching Claude Code, and
  none of the pre-flight checks would run.

### D-25: Read-only verified through discovery, rejection and source
- **Live `tools/list` through the launcher:** **71 tools**, **0** with a `create_`/`update_`/`delete_`
  prefix. This matches the source count from Phase 1 (40 `get` + 29 `search` + 2 `read`):
  - 11 financial reports: `get_profit_and_loss`, `get_balance_sheet`, `get_cash_flow`,
    `get_trial_balance`, `get_general_ledger`, `get_customer_sales`, `get_aged_receivables`,
    `get_customer_balance`, `get_aged_payables`, `get_vendor_expenses`, `get_vendor_balance`
  - 2 company/settings: `get_company_info`, `get_preferences`
  - 29 `search_*` (accounts, customers, vendors, invoices, bills, journal entries, budgets, etc.)
  - 28 get-one-record (`get_*`, legacy hyphenated `get-bill` and `get-vendor`, `read_invoice`, `read_item`)
  - 1 document export: `get_invoice_pdf` (local disk writes stay off; `QBO_PDF_OUTPUT_DIR` is unset)
- **Safe rejection:** calling `create_customer`, `update_invoice`, `delete_invoice` and
  `update_company_info` by name returns "tool not found" from the MCP layer. No QuickBooks request is
  attempted and no record is touched.
- **Source:** these tools are never *registered* (`register-tool.ts`). Read handlers call only
  `get*`/`find*`/`report*` (Phase 1).
- **Still true:** the OAuth grant has write scope. This is a client-side control (D-09).
- **Finding:** the server returns tool failures as text beginning `Error:` **without** the MCP
  `isError` flag, so a client can't tell failure from success by protocol alone. The smoke test checks
  for the prefix explicitly. When interpreting tool output, Claude has to treat an `Error:` text as a
  failure.

### D-26: Token lifecycle: verified facts, observations and sources
| Item | What I can stand behind | Basis |
|---|---|---|
| Access-token lifetime | **60 minutes** | **Observed:** `expires_in = 3600` (stored expiry exactly +60 min). Intuit help article *Handling OAuth token expiration* says the same |
| Refresh-token inactivity window | **Rolling ~100 days**, extended on every refresh | **Observed:** `x_refresh_token_expires_in` gave an expiry exactly **101 days** (8,726,400 s) after issue. Intuit's Authorization FAQ describes the expiry as rolling |
| Refresh-token absolute maximum | **5 years** (accounting scope: tokens from Oct 2023 onward; the first expire Oct 2028) | Intuit blog *Important changes to refresh token policy* (2025-11-12) and the Authorization FAQ, **as surfaced by web search**. The primary pages are client-rendered (and Medium returned 403), so I couldn't fetch them verbatim. Treat as cited, not independently verified |
| Rotation | The refresh-token *value* can change roughly every **24–26 h**; apps must always store the latest value returned | Intuit help article and community answers (search-surfaced). **Observed:** three refreshes within ~35 minutes (Django at check-out, then the MCP server twice) all returned the **same** value, consistent with periodic rather than per-call rotation. A rotation has not been observed yet (needs more than 24 h) |
| Old value after rotation | Becomes invalid (`invalid_grant`) | Upstream server comments and community reports. **Not verified by me** |

- **Risk of two refreshers:** once Intuit rotates, whoever made that refresh holds the only valid
  value. If Django and the MCP server both refreshed from their own copies, the one that didn't persist
  the new value is stranded with a dead token. That means a surprise `invalid_grant`, a forced
  re-authorization, and on the MCP side upstream's sandbox interactive-OAuth fallback (D-07).
- **How the design prevents it:**
  1. Exactly one owner per connection (`token_owner`, D-16). Django's only refresh path refuses while
     the connection is checked out.
  2. Check-in requires the server to be stopped (process detection).
  3. Inside Django, a lock plus a row lock with a re-check.
  4. On the MCP side, several server processes (an interactive Claude Code session, `claude mcp list`
     health checks, the smoke test) share **one** store file. That is the multi-process case upstream
     designed for: it persists rotations immediately and re-reads the file once on `invalid_grant`.
- **Residual risk (accepted for the local demo):** two MCP processes refreshing at the exact moment of
  a 24-hour rotation. Upstream's re-read retry covers the common ordering. A team deployment should run
  a single server instance per connection (see `CONNECTION.md`).

### D-27: Registration with Claude Code: project scope, approval, and the working-directory catch
- `claude mcp list` / `claude mcp get quickbooks-sandbox`, run from the repo root, show
  `Scope: Project config (shared via .mcp.json)`, `Type: stdio`, `Command: node`,
  `Args: connection/scripts/mcp_launch.mjs`, the four non-secret env values, and status
  **"⏸ Pending approval (run `claude` to approve)"**.
- Claude Code docs (code.claude.com/docs/en/mcp): *"For security reasons, Claude Code prompts for
  approval in interactive sessions before using project-scoped servers from `.mcp.json` files … To
  reset those approval choices, run `claude mcp reset-project-choices`."* Also: *"In `claude -p`
  runs … it loads project-scoped servers without asking."* Approval is the user's decision, so I did
  not pre-approve it (for example via `enableAllProjectMcpServers`).
- **Working-directory catch:** project scope means the `.mcp.json` at the session's project root. The
  build session runs with `E:\RE-Finance` as its root, one level *above* the repo, so it will never load
  this server, restart or not. An interactive session has to be started **in**
  `E:\RE-Finance\qbo-claude-exercise`.
- **Restart:** the docs don't say whether a running session picks up a newly added `.mcp.json`. I
  treat it as "start a new session in the repo root and approve the server". Whether that worked is
  confirmed afterwards with `/mcp` and `claude mcp list`.
- Tool output limit to watch: Claude Code warns at 10,000 tokens and caps MCP output at 25,000 tokens
  by default (`MAX_MCP_OUTPUT_TOKENS`). Large reports such as the general ledger or a monthly P&L could
  hit it. This is checked in Phase 5.

---

## Phase 5: Proof and evidence (2026-10-12)

### After Checkpoint 3
- `claude mcp list` from the repo root: `quickbooks-sandbox: node connection/scripts/mcp_launch.mjs - ✔ Connected`.
  `claude mcp get`: `Scope: Project config`, `Status: ✔ Connected`. This also confirms Claude Code
  spawns project stdio servers with the repo root as working directory, so the **relative** launcher
  path in `.mcp.json` resolves.

### D-28: How "works" was proven, and kept separate from model judgement
- **Ground truth:** the same MCP tools were called directly through the launcher, and the raw JSON was
  parsed in code (no model).
- **Claude:** three `claude -p` runs from the repo root, restricted to this server:
  `--tools ""` (no built-in tools), `--strict-mcp-config --mcp-config .mcp.json` (none of the user's other
  connectors), `--allowedTools mcp__quickbooks-sandbox`, `--no-session-persistence`, a budget cap, and
  `stream-json` capture of every tool call and result.
- I chose headless runs because the build session is rooted one folder above the repo (D-27), and
  because a stream capture gives an auditable record of *which tool produced which number*.
  The Claude Code docs state `claude -p` loads project servers without the approval prompt. The user
  had also approved the server interactively, as shown above.
- **Results** (details: `evidence/phase5_ground_truth.md` and `evidence/phase5_claude_runs.md`):
  - **Run 1, data questions:** every figure matched the ground truth. Company; 90 accounts (89 active
    + 1 inactive; my first ground truth counted only the 89 active); 29 customers; 26 vendors; monthly
    P&L, net income 1,642.46; balance sheet, assets 23,436.29. Claude disclosed two HTTP 400 failures
    instead of guessing. 25 turns, $0.81.
  - **Run 2, the demo question:** Q3 2026 net income 1,585.21. The top three expense accounts were given
    under both definitions (top-level vs. leaf), with Miscellaneous 2,916.00 flagged. 3 turns, $0.11.
  - **Run 3, attempted create and delete:** 71 tools, 0 mutating. Claude made only read lookups,
    refused, and explained the server is read-only. $0.05.
- The smoke test (`connection/scripts/smoke_test`, 11 checks) passed on every run: 11/11, including
  the Django `/test` endpoint, served from the access token cached at check-out.

### D-29: Integration findings to carry into Tasks 2–4
1. **`search_accounts {count:true}` → HTTP 400**, and the accounts handler ignores `totalCount` anyway.
   Count accounts from the list. Customer and vendor counts work. Adding an `Active=false` filter to a
   count query also returned 400.
2. **Unflagged tool errors:** failures arrive as text (`Error …`) with no `isError`. Skills and evals
   must check for that text.
3. **Output size vs. Claude Code's 25k-token MCP cap:** a 12-month **by-month** P&L is about 21k tokens.
   In Run 1 Claude re-queried month by month (12 extra calls). Task 2's skill should ask for bounded
   periods.
4. **"Top three expense accounts" is ambiguous** (parent vs. leaf; *Other Expenses* in or out). That
   makes it a good golden case for Task 3. The expected answers are in `phase5_ground_truth.md`.
5. When refusing writes, Claude **suggested** enabling write tools. A project `CLAUDE.md` or the Task 2
   skill should state that read-only is a deliberate policy, so it isn't offered as a fix.
6. **Rotation still not observed:** after Django's check-out refresh and eight MCP-side refreshes (one per
   tool-calling server start: 3 smoke tests, 2 ground-truth scripts, 3 Claude runs) over about two hours, the refresh-token value is unchanged. This fits Intuit's
   "about every 24–26 h" guidance. A rotation and its check-in import are covered by unit tests, not yet
   by a live event.

### Evidence policy
- Committed: `evidence/phase5_smoke_test.json`, `evidence/phase5_claude_runs.md` (tool inputs plus
  Claude's answers verbatim), `evidence/phase5_ground_truth.md`. They hold sandbox figures and the
  `9341…` realm hint only.
- Git-ignored: `evidence/raw/` (full tool outputs and stream captures).
- Checked by script: none of the full realm ID, refresh token (DB and store), client ID, client secret,
  Fernet key or Django key appears in any committed evidence, any `*.md`, or `.mcp.json`. `secret_scan
  --all` is clean.

### Docs written
- `TROUBLESHOOTING.md`: the nine required cases, each with exact messages from this project, plus
  "expected behaviours that look like errors". While writing it I caught and fixed one wrong claim of
  my own: opening the console via `127.0.0.1` does **not** break CSRF (Django compares `Origin` with the
  request host). It only breaks the OAuth callback, through the cookie host.
- `DEMO_SCRIPT.md`: the five-minute demo built around check-out, then Claude, then check-in, with the
  answer key, what a good answer includes, and three live-modification requests with exact files and
  commands.

---

# Task 2: Monthly trend-analysis skill (2026-10-12)

The skill is at `.claude/skills/monthly-trend-analysis/`. Run it with
`scripts/run_trends.py [workbook]`, or let Claude invoke it from a request (verified: it triggers
without being named). Tests: `.venv/Scripts/python -m unittest discover -s tests`, 27 passing.

### D-30: Code lives inside the skill folder, not in `connection/analysis/`
- **Choice:** `.claude/skills/monthly-trend-analysis/` holds everything:
  - `SKILL.md`
  - `scripts/run_trends.py` plus the `scripts/trends/` package (`workbook.py` extraction, `mapping.py`,
    `analysis.py`, `report.py`)
  - `references/` (`category_map.json`, `extraction-rules.md`)
  - `tests/` (with the portability workbook builder and `test_data/`)
  - `requirements.txt`, and a git-ignored `.venv`
- **Why:**
  - `connection/` is Task 1's QuickBooks plumbing, and this code never touches QuickBooks.
  - Keeping the skill self-contained means a teammate can copy one folder to another repo or client and
    it works.
  - Skill-creator guidance puts deterministic code in `scripts/` and on-demand docs in `references/`.
  - Tests sit next to the code they protect.
- **Dependency:** `openpyxl` 3.1.5 is pinned in `requirements.txt` and installed into the skill's own
  `.venv`, which leaves the system Python untouched. The xlsx skill described `openpyxl` as
  preinstalled, but it wasn't on this machine; the script prints setup instructions if it's missing.
  No pandas: the logic is row-structural, and stdlib plus openpyxl is enough.
- **Input file:** the provided workbook is named `ABC Inc - Financial Statements (1) (1).xlsx`, not
  the name in the brief. I didn't rename user data. The script defaults to *the single `.xlsx` in
  `data/`*, so no filename is hardcoded.

### D-31: The subtotal-detection rule is structural (stack of open sections), and formatting is not trusted
- **Observed in the real file** (inspected cell by cell before writing logic):
  - indent is 0 on every row;
  - bold is inconsistent (`Total S & M Payroll` is bold, `Total Income` is not);
  - the two sheets use different label columns (B vs C) and month formats (`Jun 2026` vs `30 Jun 2026`);
  - subtotals are `=SUM` formulas, details are values;
  - `Total Operating Expenses` = `SUM(direct accounts) + Total S & M Payroll + Total Marketing`, so
    summing every row would double-count two groups.
- **Rule:**
  - **HEADER:** a label with no value in any month. It opens a section.
  - **TOTAL:** `Total X` / `Total for X` where X is an open section. It closes the section; its values
    are the stated subtotal.
  - **DETAIL:** a label with values inside a section. These are the only rows summed.
  - **SUMMARY:** values outside every section (Gross Profit, Net Income). Used only for cross-checks.
  - **Fallbacks, each warned:**
    - a header-less Total: the group is inferred from the shortest preceding run of rows that sums to
      it in every month;
    - an unreconcilable Total: excluded and flagged;
    - a header never closed: treated as an all-blank account, with its rows returned to the parent;
    - a formula in a detail row: flagged as a possible hidden subtotal.
- **Rejected:**
  - indentation or bold (absent or inconsistent here);
  - the `": "` naming pattern (in this file that's QBO sub-account naming, `Marketing/Advertising: Ad
    Spend`, not subtotal structure);
  - formulas as the primary signal (formula-free exports exist; formulas are used only for warnings).
- **Cross-check:** every stated subtotal is compared with its detail sum per month (tolerance 0.01).
  - A mismatch is a warning showing both numbers; the analysis uses detail rows, and the reviewer decides.
  - Gross profit, operating income and net income are recomputed and compared with the sheet's rows.
  - Assets are checked against liabilities plus equity.
  - **ABC Inc result:** 15 subtotal rows × 18 months, 0 mismatches. All recomputed rows match, and the
    balance sheet balances.
- **Independent verification:** a separate script read the raw cells with plain `openpyxl`, bypassing
  the extraction code, and matched Total Income, Gross Profit, Total Operating Expenses, Net Income,
  Usage Fees and Total Cash in all 18 months (max diff 0.0000), plus TTM revenue (2,303,975.51) and
  June GM% (70.15).

### D-32: Output = a JSON contract plus a Markdown draft with a narrative slot Claude fills
- **Choice:** the script writes `<company>-<YYYY-MM>-trends.json`, where every number lives (schema in
  `references/extraction-rules.md` §6), and a Markdown report with these sections:
  1. commentary slot
  2. rule-based flags
  3. revenue by stream (values, MoM %, YoY %, TTM, share)
  4. gross margin trend (with TTM GM %)
  5. opex by category, as-exported and excluding non-operating items
  6. movers
  7. net income
  8. balance sheet snapshot
  9. data quality
  10. account-to-category appendix, and a reviewer checklist

  Claude replaces the narrative marker with 4–8 bullets written **only** from figures in the report.
- **Why:**
  - Numbers stay deterministic and testable; the JSON is also what Task 3's evals can assert on.
  - Markdown is diffable, renders in GitHub and VS Code, and a reviewer can edit it directly.
  - Keeping the computed figures separate from the model's prose keeps every claim traceable.
- **Rejected:**
  - An Excel output: heavier formatting work, harder to diff or evaluate; easy to add later from the JSON.
  - Prose only: numbers would be untraceable.
  - Letting Claude compute figures: not reproducible.
- **Grounding check, run on both final reports:** every number in the narrative was searched for in the
  generated sections. ABC: 54 of 55 found; the exception is "roughly 700–1,250", Claude rounding a
  flagged 721. Bluebird: 41 of 41. That's a candidate eval for Task 3.

### D-33: The "Other" bucket in practice
- Categories come from ordered keyword rules in `references/category_map.json`. The first match on the
  account name, then its `Parent:` prefix, then enclosing group names, wins. The extraction never uses
  the map, and an unmatched account goes to **Other Opex**, listed by name in the report and the flags.
- **ABC Inc:** one account, **General Expenses**. TTM 16,158, about 0.3% of underlying TTM opex
  (5,999,465). Typically 125–325 a month, but 12,103 in Jan 2026.
- **Bluebird (portability):** three accounts.
  - **Instagram Ads** is really marketing. The rules have no "ads" pattern, and I deliberately didn't
    add one, to show how a mapping gap surfaces.
  - **Mystery Shopper Program** is genuinely unclassifiable.
  - **Supplier Rebates** is a negative contra account.
  - Lesson: "Other" is where per-company mapping gaps and contra accounts show up. The fix is a
    company-specific copy of the JSON (`--config`), never code.
- **Non-operating category:** ABC's export places Income Tax Benefit, Interest Income and Interest
  Expense inside Operating Expenses. They're grouped as "Tax & Interest (non-operating)" and shown next
  to "opex excl. non-operating"; totals are never changed. This matters: Dec 2025 net income is
  +534,551 only because of a -1,244,430 Income Tax Benefit. Excluding non-operating items it's -715,902.
  Reclassifying is left to the reviewer.

### D-34: Portability test, and what had to be generalised
- **Workbook:** `tests/test_data/bluebird-bakery.xlsx`, built by `tests/build_test_workbooks.py`. It
  differs from ABC on every axis:
  - company before report title; header on row 4; a single label column;
  - months oldest-first as real date cells; 9 months only; a trailing "Total" column;
  - values only, no formulas;
  - `Total for X` style;
  - a group with no header (`Total Delivery`) and an all-blank account mid-list;
  - blank cells, a negative contra account and a negative revenue month;
  - a stream that's new in the latest month, and an Other Income section;
  - `Net Profit` instead of `Net Income`;
  - **one deliberately wrong subtotal** (+25.00 in Mar 2026);
  - a Balance Sheet with labels in column B and `Sep-26` text headers, newest-first.
- **Result:**
  - It ran first time without a crash, and the figures were correct (hand check: Sep revenue
    49,200 + 15,700 + 3,800 + 600 + 12,000 = 81,300).
  - The deliberate mismatch was caught, and the header-less group was inferred.
  - Net Profit (including Other Income) and Gross Profit reconcile; Operating Income is reported as
    "skipped" (no such row); the Balance Sheet balances.
  - Unmapped accounts went to Other; TTM and YoY show "n/a" with fewer than 12 months.
- **What I had to generalise.** I didn't change the test data at any point.
  1. **Built in from the start**, because ABC's two sheets already differ:
     - "Account" header detection with many month formats, and labels in any column left of the months;
     - month sorting, sheet discovery by name patterns, and company name regardless of title order;
     - `Total for X` matching, and section roles from config patterns.
  2. **Found while designing the test, fixed before the first run:** an account blank in every month
     looks exactly like a header, so it captured the rows after it. Now an unclosed header becomes a
     zero account, and its rows go back to the parent.
  3. **Found in the first run (noise, not wrong numbers):**
     - a line non-zero only in the latest month was double-reported as both "new" and a "spike";
     - a material 6-month cash decline wasn't flagged because the rule only checked month-over-month.
  4. **Found when Claude used the skill on Bluebird. Both were my report's fault, not the model's:**
     - The movers table printed "new" whenever the prior month was 0, so Claude called a quarterly
       expense (400 in Mar, Jun and Sep) "new". It's now labelled "from 0", and `SKILL.md` says to call
       a line new only when a flag does.
     - Percentages were double-rounded (59.551 → 59.55 → "59.5%") while the flags showed "59.6%".
       Claude noticed and asked the reviewer. Percentages are now stored to 4 decimals.

     Both have regression tests.
- **Tests:** 27, covering units, synthetic sheets (double counting, mismatch, inference, unmatched
  total, blank header, blank cells, formula in detail, column order), real-workbook checks against raw
  rows, portability, and the CLI. A mutation check (Totals treated as detail; cross-check disabled;
  categorisation disabled) made the suite fail every time.

### D-35: Known limits of the skill (stated in `SKILL.md`)
- **No forecasting and no accounting judgments.** It doesn't reclassify accounts, decide what is
  one-off, choose between conflicting subtotals, or estimate runway. Those stay with the reviewer.
- **Thresholds are heuristics.** The spike rule is noisy on ABC: 6 listed, plus 39 smaller ones counted.
  Category rules are order-dependent (e.g. "Sales & Marketing - Travel, Meals & Entertainment" lands in
  Sales & Marketing).
- **Data needs:** YoY needs 13+ months, and TTM needs 12+.
- **Evidence base:** tested on two workbooks, one real and one synthetic. Real exports from other QBO
  regions or versions may surface new header or period formats; the parser warns rather than guessing.

### D-36: Stretch goal (load this workbook into the sandbox, then re-run the skill on live QBO data) is deferred, not abandoned
- **Decision (2026-10-12):** sequence it last, after Task 3 (evals) and Task 4 (architecture note),
  because of the 7-day deadline. Tasks 3 and 4 are graded deliverables; the stretch goal is optional.
- **Planned approach when picked up:** a separate, throwaway write script with its **own short-lived
  OAuth grant** against the sandbox. It would create the workbook's accounts and post about 18 months of
  journal entries to reproduce the balances, then re-run the skill on the sandbox's monthly P&L export.
  The Task 1 read-only MCP setup (`.mcp.json`, launcher, `QUICKBOOKS_DISABLE_*` flags) and Django's
  OAuth and token code stay untouched.
- **Known caveat to resolve first:** the current sandbox already holds Intuit's sample data, so the
  result would be "ABC plus sample data" unless a fresh sandbox company is used.

---

# Task 3: Evaluation suite (2026-10-12)

The suite lives in `evals/`, documented in `evals/README.md`. It runs **7 golden cases** end to end through
the real skill (`claude -p`), plus the skill's 28 regression tests. Commentary is graded by a separate
Claude call. Both layers are summarised in one report.

### D-37: A 28th regression test closes a real extractor-layer gap
- Added `test_ttm_mom_and_yoy_math_matches_raw_cells` to `RealWorkbookTests` in
  `.claude/skills/monthly-trend-analysis/tests/test_trends.py`.
- **Why:** the 27 committed tests checked the monthly series against raw rows, and MoM only through flag
  text. Nothing asserted the **TTM, prior-month TTM, MoM %, YoY %, TTM GM % or TTM net income values**,
  or that TTM starts in month 12.
- The test reads the raw ABC cells itself and asserts all of these. It only adds assertions and changes no
  behaviour. It passed on first run, so the TTM math was already correct.

### D-38: Contamination incident in the first run, and the harness hardening
- **Incident:** in `evals/runs/first-run-20261012`, case a's X5 ("nothing outside evals/runs/ changed")
  FAILED. The changed file was `evals/README.md`, written by the operator (this build session) at
  13:28:27 IST, during case a's skill run (13:27:52–13:28:34). The skill's only edit was its own report
  under `evals/runs/`. **This was neither a skill defect nor a wrong golden**; the check caught a real
  out-of-band change. The run folder is kept unedited, with an explanatory `NOTE.md`.
- **Hardening (harness only):**
  - **Content hashes, not `git status`:** `run_evals.py` now snapshots the sha256 of every tracked and
    untracked-but-not-ignored file outside `evals/runs/`, and the submodule's checked-out commit. Status
    lines alone miss a file that was already modified and changes again.
  - **Run-level guard:** the harness snapshots at the start and checks after the regression tests, after
    each case, and after the calibration and controls. Any change a skill run didn't make itself is reported
    as **`harness contamination: <path> modified during run (during <phase>, between t0 and t1)`**. It is
    reported in its own report section, separate from the skill checks, and the run exits with code 3.
  - **X5 is now attributed:** a change made by the skill's own tool calls (Write/Edit target, or a path
    named in a Bash command) is a skill FAIL. A change in the skill's window that its calls don't account
    for makes X5 **BLOCKED**, because that window is contaminated. It never defaults to PASS.
- **Tests:** `evals/tests/test_harness.py`, 5 tests in a throwaway git repo. They cover: the message fires
  for a modified file; an already-dirty file edited again is caught; created and deleted files are caught;
  `evals/runs/` and git-ignored files are excluded; attribution splits skill writes from operator writes.
  All pass. The skill, goldens and grader rubric are unchanged.

### D-39: Deleted `evals/runs/harness-smoke-1/`
- It was a one-case plumbing check of the harness (case g only), run before the first honest run and
  labelled as such. It was **not an evaluation**, and its results were never reported as one. Deleted to
  avoid confusion with real runs.

### D-40: Rounding policy, and the ruling on "721 → roughly 700"
- **Policy (stated once):** in `evals/goldens/cases.json` → `rounding_policy`, and passed verbatim to the
  grader. Prose may round within **5% relative** (or **0.5 pp** for percentages) if sign, direction,
  ranking and thresholds are unchanged. Structured JSON must meet each check's explicit tolerance
  (currency ±0.01, percentages ±0.01 pp).
- **Ruling:** Task 2's "roughly 700–1,250" for the true averages 721.0033 / 998.51 / 1,045.46 / 1,250.00
  (`Income Statement!D68:I68` etc.) is **acceptable**. 700 is −2.9% from 721; the range bounds all four
  values; no ranking or direction changes.
- **Not special-cased:** case b applies the same policy to every fresh run, and the calibration step had
  the grader rule independently on the frozen Task 2 text. It agreed (PASS, "about 2.9% below 721") in both
  runs. Documented in `evals/README.md` § Rounding policy.

### D-41: The baseline comes from the clean run, not the first run
- `evals/baseline/` is a verbatim copy of `evals/runs/clean-run-20261012`, with its console log and
  `BASELINE.md`. **121/121 checks PASS, 7/7 cases, no contamination, 28/28 regression tests, all 3 grader
  controls agree.**
- **Why not the first run:** its single FAIL was caused by the operator, not the skill. A baseline built
  from it would encode an incident as if it were skill behaviour. The first run is kept, unedited, as the
  record of the incident.
- Provenance is in `BASELINE.md`:
  - source run;
  - git HEAD `396f17d`, with the Task 3 files uncommitted at the time;
  - Claude Code 2.1.296;
  - skill model `claude-opus-5-5` (reported);
  - grader model `claude-sonnet-5-5`, plus `claude-haiku-5-5` for Claude Code background work;
  - cost $2.74;
  - the sha256 of `results.json`.

### D-42: Cost per evaluation run (input for Task 4's 10-client question)
| Run | Skill runs (7) | Grader calls (11) | Total |
|---|---:|---:|---:|
| first-run-20261012 | $2.47 | $0.27 | $2.73 |
| clean-run-20261012 | $2.47 | $0.27 | $2.74 |

- These are Claude Code's reported `total_cost_usd`, at list prices.
- **Per skill run** (one company, one month): $0.29–0.43, mean **≈ $0.35**, 7–10 turns, about 40–60 s.
  **Per grader call:** ≈ $0.025.
- **A full eval suite** takes about 7 minutes run sequentially.
- **Scaling, as rough arithmetic and not a forecast:**
  - one monthly report per client for 10 clients ≈ 10 × $0.35 ≈ **$3.50 per month** in model cost;
  - re-running this 7-case suite per skill change ≈ **$2.75**;
  - each extra per-client golden case adds ≈ $0.38 (skill run plus grader).

### D-43: Run-to-run variance, first run vs clean run (the first evidence)
- **Verdicts:** the only flip in 121 checks was case a X5, FAIL → PASS (the contamination, resolved).
  Every structured check, and every required and forbidden claim, had the same verdict in both runs.
- **Structured values:** identical in all 7 cases. The extractor is deterministic, as expected.
- **Commentary differs materially in content, though not in verdicts:**
  - Length varies by up to about ±15% (293–448 words, 7–8 bullets).
  - Only **55–78%** of the cited figures overlap between runs (Jaccard). Part of that is formatting
    (`-1,800` vs `1,800`, `2,200.00` vs `2,200`); part is real choice of what to mention.
  - Notably, case b's clean run gave **no** prior-6-month averages for the four "vanished" lines. It read the
    monthly history in the JSON instead and **argued with the flag's framing** ("not clean June
    drop-offs": Advisory Services has been 0 since Feb 2026; Professional Fees posted in only 2 of 18
    months). I checked every figure it cited against the raw cells (1,119.31; 1,561.67; 2,500 in Jan 2026;
    2,500 and 3,772.77), and **all are correct**.
- **Two findings, not yet acted on:**
  1. **Grader coverage gap:** the grader only verifies figures among a case's reference facts. A run that
     cites other true or false figures, such as the monthly values above, passes or fails without those
     being checked. A deterministic grounding check is a candidate harness addition: every number in the
     commentary must appear in the run's JSON or report.
  2. **Skill flag semantics:** the "vanished expense line" rule fires when the latest month is 0 and at
     least two lookback months were material. It therefore labels lines as "zero in Jun 2026" that stopped
     months earlier (Advisory Services: zero since Feb). The commentary corrected this in one run of two.
     Changing it would change skill behaviour, so it needs a decision first.
- **Interpretation:** two runs is too few to estimate flakiness rates. They show verdicts are stable here,
  while the commentary's content and emphasis vary. Repeat runs (for example 3–5 per case) before treating
  any single verdict as definitive.

### D-44: Number-provenance check (P1): deterministic, harness and grading only
- **Why:** D-43 found that the grader only verifies figures among a case's reference facts. A run could
  cite other figures, true or false, that nothing verified.
- **What:** `evals/provenance.py`. Every number in the commentary must match a value in **that run's own**
  `*-trends.json` (any numeric field) or `*-trends.md` (any number in the report). The harness runs it as
  check **P1** for every case, and it counts in the score. Any unmatched number fails P1, and the report
  lists it with its sentence. No model is involved.
- **Matching = the rounding policy, made precise for a large candidate pool:**
  - The number must be a plausible rounding of a candidate **at the precision it is written in** (1,045 →
    ±0.5; 700 → ±50; 70.2% → ±0.05; 1.87M → ±5,000).
  - It must **also** be inside the policy band (≤5% relative; ≤0.5 pp for percentages).
  - Magnitudes are compared, because prose carries the sign in words ("down 215,543"); direction stays the
    grader's job.
  - A plain 5% band was rejected: against thousands of candidates it matches almost anything.
- **Explicit ignore list (in the code, each rule documented):**
  - year (1990–2100, plain);
  - day of month next to a month name;
  - count: an integer + a count noun, with at most one *whitelisted* descriptor;
  - `N of M`;
  - `N-month` spans;
  - section/step/`D-` references.
- **Bugs found by the check's own tests, fixed before commit:**
  1. The count rule first allowed *any* word before the noun, so "rose by 400 **this** month" was ignored.
     It now accepts only a short descriptor whitelist ("subtotal", "consecutive", "expense", …).
  2. "D-04" leaked "04". Fixed.

  Re-running on both saved runs after the fixes gave the same classifications, so neither bug had hidden a
  real figure.
- **Result on saved commentary** (no new skill runs): first run 7/7 PASS, baseline 7/7 PASS, **0 unmatched
  numbers in 14 commentaries** (matched 43–54 and ignored 11–25 per case). Nothing to rule on, so no ignore
  rules were added to make anything pass. Recorded as the addendum in `evals/baseline/BASELINE.md`, with
  per-number detail in `provenance_addendum_v1.json`.
- **Discrimination check (planted into a copy of the real commentary):** caught a random 6-digit figure, a
  self-computed sum (526,654.24), a true value at the wrong precision (195,900.00 for 195,898.16) and an
  unknown percentage. Honest rounding ("about 196,000", "roughly 70%") passed.
- **Known limitation, pinned by a test:** a *round* number can match an unrelated value. "About 300,000"
  for a 330,756 loss matched COGS TTM 299,409 by coincidence, and "2,000" matched a stray monthly value.
  P1 proves a figure exists in the output, not that it belongs to the right label; that remains the
  grader's job (F4 checks named facts).
- **Tests:** `evals/tests/test_provenance.py` (20), covering parsing, every ignore rule, matching
  (including the 721 → "roughly 700" ruling), the precision and policy failures, sentence reporting, the
  limitation, and real baseline artifacts. Harness tests are now 25 in total.
- **Also in this commit:** `run_evals.write()` now writes LF line endings, so future run artifacts hash the
  same before and after git (the CRLF issue found while fingerprinting baseline v1).

### D-45: Intentional skill behaviour change: "vanished" expense lines say "has been zero since <month>"
- **Defect (found in D-43):** the vanished-expense-line flag always said "is zero in <latest month>", even
  for lines that had stopped months earlier. ABC's Advisory Services had been zero since Feb 2026, and
  Professional Fees since Apr 2026, yet both read as if they had stopped in June.
- **Change** (`analysis.py`, `_flag_opex`, approved as shown):
  - The flag finds the last non-zero month before the latest month.
  - If that month is the prior month, the wording is unchanged: "is zero in <latest>".
  - Otherwise it says **"has been zero since <first zero month> (last non-zero: <month>, <value>)"**.
  - The trigger rule itself is unchanged.
- **ABC effect** (from raw cells):

  | Line | New wording | Source |
  |---|---|---|
  | Advisory Services | since Feb 2026; last non-zero Jan 2026, 2,500 | `IS!H30` |
  | Professional Fees | since Apr 2026; last non-zero Mar 2026, 3,772.77 | `IS!F85` |
  | Federal & State Taxes | "is zero in Jun 2026" (unchanged) | May value 1,561.67, `IS!D40` |
  | Marketing/Advertising: Miscellaneous | "is zero in Jun 2026" (unchanged) | May value 1,119.31, `IS!D68` |

  Bluebird has no vanished lines.
- **Test 29:** `test_vanished_line_wording_says_zero_since`. Skill regression tests: 29.
- **Golden change in case b. This is an intentional behaviour change, not a fit-to-pass**:
  - S2 (Advisory) and S5 (Professional Fees) now require the "has been zero since …" text.
  - New S6 and S7 forbid the old "is zero in Jun 2026" wording for those two lines.
  - S3 and S4 are unchanged.
  - The new facts `abc.vanished.*.last_nonzero_month` and `*.last_nonzero_value` in `derive_facts.py` make
    the expected months and values auditable to their cells.
  - Recorded in the case's `_change_log` too.
- **Deliberately no new commentary claim for case b:** a forbidden claim such as "says Advisory Services
  stopped in Jun 2026" would make grading flaky, because "Advisory Services is zero in Jun 2026" is still
  literally *true*, and a grader could reasonably go either way. The wording is checked
  **deterministically** in the structured checks (S2, S5, S6, S7) instead.
- `SKILL.md`: one sentence asking the commentary to keep the "zero this month" vs "zero since" distinction.

### D-46: Known limitation (not changed): the vanished flag goes quiet after a while
- The flag only fires while **at least 2 of the prior 6 months were material**. A line that went to zero
  and stays at zero drops below that within a few months, after which it is **not flagged at all**.
  Advisory Services, for example, will stop being flagged as its last material months roll out of the
  6-month window.
- This is acceptable for a month-over-month review, which asks what changed recently. Long-dormant lines
  are visible in the account appendix as zeros. Recorded as a limitation, with no change made.

### D-47: Regression run for D-45; baseline v2
- **Prediction, stated before the run:** only case b changes. It gains S6/S7, and S2/S5 now match the "has
  been zero since" text. Every other case keeps the same verdicts and structured values. P1 runs live
  everywhere and passes.
- **Run** `commit3-run-20261012`: **130/130 checks PASS** (121 as in v1, + 7 live P1, + case b's S6/S7),
  7/7 cases, no harness contamination, **$3.04**.
- **Diff vs v1** (`python evals/compare_runs.py`): **only case b differs**, exactly as predicted. Its S2/S5
  actual text changed to "has been zero since Feb 2026 (last non-zero: Jan 2026, 2,500)" and "since
  Apr 2026 (last non-zero: Mar 2026, 3,773)", and S6/S7 were added. No verdict flipped anywhere, and no
  other structured value changed. P1 passed in all 7. The commentary followed the new wording without
  being told: "'Advisory Services' has been zero since Feb 2026 (last non-zero: Jan 2026, 2,500)".
- **Cost +$0.30 vs v1:** extra turns in cases e (13 vs 9) and f (18 vs 10). Case f is Bluebird, which
  D-45 cannot affect, so this is run-to-run variance in agent behaviour, not the change.
- **Baseline v2** = verbatim copy of this run, in `evals/baseline/commit3-run-20261012/`. **v1 moved with
  `git mv` to `evals/baseline/history/v1/`**, its BASELINE.md unchanged, so nothing is overwritten. The new
  `evals/baseline/BASELINE.md` has a version table (v2 current, v1 history).
- `test_provenance.py`'s real-artifact tests now point at the moved v1 folder. Left on the old path they
  would have *silently skipped*.
- **New tool:** `evals/compare_runs.py <old> <new>`, a per-case, per-check diff (verdicts, structured actual
  values, added/removed checks, P1, cost). Its first version wrongly counted "P1 newly live" as a
  difference in its summary line; fixed before use.

### D-48: Same "has been zero since" logic for the revenue-stream flag (intentional behaviour change)
- **Change** (`analysis.py`, `_flag_revenue`): a stream that is zero in the latest month after a material
  month in the lookback window says **"has been zero since <first zero month> (last non-zero: <month>,
  <value>) after <peak> at its peak…"** if it stopped before the latest month. If it really stopped in the
  latest month, the text is **byte-identical** to before ("is zero in <latest> after …").
- **Affected lines** (from raw cells):

  | Workbook | Stream | Effect | Source |
  |---|---|---|---|
  | ABC | **SKU Profiling** | now "has been zero since May 2026 (last non-zero: Apr 2026, 10,000)" | `IS!E13` |
  | ABC | Partnership Income | unchanged | May 476.73, `IS!D9` |
  | ABC | Professional Services | unchanged | May 833.33, `IS!D10` |
  | Bluebird | (none) | no stream triggers the flag | — |
- **Test 30:** `test_vanished_revenue_stream_wording_says_zero_since`. Skill regression tests: 30.
- **Golden change, in case a** (the core revenue case): S17 requires SKU Profiling's new wording; S18 forbids
  its old "is zero in Jun 2026". New facts `abc.sku_profiling.*` (cells C13, D13, E5, E13). No commentary
  claim is added, for the same reason as D-45. Intentional behaviour change, not a fit-to-pass.
- **PREDICTION, written before the run:** only **case a** changes: it gains S17 and S18, both PASS, with no
  verdict flips. Every other case (b–g) keeps identical verdicts and identical structured actual values.
  The ABC reports in cases b and e contain the SKU flag text, but none of their checks reference it. P1
  passes in all cases. Commentary content will vary as usual (D-43).
- **Result of the commit-4 run (`commit4-run-20261012`): FAIL, recorded honestly.** Case a changed exactly as
  predicted (S17/S18 PASS), but **case b's F2 flipped PASS → FAIL**. The commentary headed the zero-lines bullet
  "Expense lines no longer recurring", which asserts permanence, and the grader caught it. Case b's structured checks
  and P1 were unchanged. **The diff did not match the prediction, so the change was blocked**: no commit and no
  baseline from that run. The run's report, results and an explanatory NOTE.md are committed under
  `evals/runs/commit4-run-20261012/`. The fix is in D-50 to D-52; the policy that now governs such flips is in D-49.

### D-49: Regression policy: resample commentary flips; deterministic checks still block on one run
- **Why:**
  - **Single-sample pass/fail on LLM prose, graded by an LLM, is noisy.** In two consecutive full runs, two
    different cases flipped once each (case b F2 in `commit4-run`, case g R1 in `commit5-run`), with nothing
    relevant to them changed.
  - **The grader disagrees with itself on identical input.** Re-grading the exact `commit5-run` case g
    commentary 3 times gave R1 **PASS, PASS, FAIL**: 2 FAIL in 4 with the original grading (D-51).
  - Blocking on one FAIL would block good changes; ignoring commentary FAILs would miss real regressions.
- **Policy** (`evals/REGRESSION.md`, `evals/policy.py`, applied in `run_evals.py`):
  - Deterministic checks (execution, structured, P1) stay **hard-blocking on a single run**.
  - A commentary claim that **flips** (FAIL now, PASS in the baseline named by `evals/baseline/current.json`; a
    claim absent from the baseline counts as a flip) re-runs that case **3 more times**, but only if its
    deterministic checks passed.
  - The case is then judged on all 4 samples: **≥2 failing blocks (FAIL); exactly 1 is UNSTABLE** (reported, not
    blocking, investigate); **0 passes**. A grader BLOCKED never counts as a pass, and a deterministic FAIL in any
    resample blocks.
  - The report shows each claim's pass rate and every sample's status and evidence. Cost and score include
    resamples; UNSTABLE is counted separately.
- **Cost logic:** resampling happens only on a flip, so routine runs stay at one sample per case (≈ $3 a run). A flip
  adds ≈ 3 × $0.45.
- **Honest limits:** with 4 samples and a ≥2 threshold, a real but rare regression can slip through as UNSTABLE, and
  noise can still block (2 grader misses in 4). It is a pragmatic threshold, not a statistical test. A claim whose
  verdict is UNSTABLE repeatedly is a signal to clarify the golden wording or the skill, not to keep re-running.
- **Tests:** `evals/tests/test_policy.py`, 15 tests:
  - flip detection (including a missing baseline and BLOCKED);
  - resample only with clean deterministic checks;
  - judging 0/1/2+ fails into PASS/UNSTABLE/FAIL;
  - BLOCKED never counted as a pass;
  - case verdict, including a deterministic FAIL in a resample.

  Eval-side tests now 40.
- **Also:** `REGRESSION.md` did not exist before this commit; the policy had only been stated in instructions.
  It is now the written source.

### D-50: SKILL.md rule: a zero line is an observation, not a conclusion (case b F2)
- **Trigger:** `commit4-run` case b failed F2 (forbidden: implying a zero line has permanently stopped). The heading
  was "Expense lines no longer recurring". Nothing relevant to that wording had changed in the skill.
- **Change:** a writing rule in SKILL.md. State only what the numbers show ("zero in Jun 2026", "has been zero since
  Feb 2026 (last non-zero Jan 2026, 2,500)"). Say that whether the line has stopped, been discontinued or is timing
  is for the reviewer to confirm. Headings count too.
- **Measured** (case b alone, 5 runs before the rule, 5 after; `evals/runs/caseb-before-1..5`, `caseb-after-1..5`):

  | Measure | Before | After |
  |---|---|---|
  | F2 FAIL | 0/5 | 0/5 |
  | Near-miss headings ("no longer appearing", "no longer posting") | 2/5 | 0/5 |
  | Explicit reviewer deferral on expense lines | 0/5 | 4/5 (after-1 lacks it) |
  | Explicit reviewer deferral on revenue streams | 0/5 | 5/5 |

- **Honest reading:**
  - F2 did not fail in any of these 10 runs. So **the measurement doesn't show the rule fixing a failure rate**:
    the original failure rate is somewhere below what 5 samples can resolve.
  - What the rule measurably changes is wording. The near-miss phrasing disappeared, and the reviewer deferral
    became nearly consistent.
  - With n = 5 per arm, 2/5 → 0/5 is suggestive, not significant.
- **Not done:** the optional check of commit 3 in a worktree. It was skipped because the "before" F2 failure rate was
  already 0/5. Cost of the 10 runs: $2.46 before, $2.72 after.

### D-51: Case g R1 is grader noise at a borderline; SKILL.md rule to name missing comparisons
- **Trigger:** `commit5-run` case g R1 flipped PASS → FAIL. R1 requires the commentary to acknowledge that TTM/YoY
  comparisons aren't available because the export covers fewer than 12 months. The only relevant sentence was "No
  same-month-last-year comparison is available, because the export starts in Jan 2026". The grader called that
  "only partly made".
- **Measured:** re-grading the **identical** commentary 3 times (`evals/runs/caseg-regrade-1..3`, $0.07) gave R1
  PASS, PASS, FAIL. With the original grading that is **2 FAIL in 4, on unchanged text**. The sample is tiny, but it
  is enough to show the verdict isn't stable at that wording.
- **Change:** a SKILL.md rule. If TTM or YoY can't be computed, say so explicitly, name which comparisons are missing,
  and give the number of months in the export. This targets the borderline: the "partly made" wording omitted TTM
  and the month count.
- **Deliberately not changed:** the R1 golden and the grader rubric. The flaky sentence was a weaker statement of the
  claim, not a correct statement graded wrongly, so loosening R1 would have hidden that.
- **Effect seen so far:** one run (`policy-run-20261013`) wrote "TTM and year-over-year figures aren't available
  because the export covers only 9 months (Jan–Sep 2026)", and R1 passed. That is n = 1; the noise rate after the
  rule isn't measured.
- **Process response:** the resampling policy (D-49).

### D-52: Full run under the resampling policy; baseline v3
- **Prediction, written before the run** (`evals/runs/policy-run-prediction.txt`, 2026-10-13T02:16:56Z): vs v2, case a
  gains S17/S18 (PASS); every other verdict and structured value is identical; any commentary flip resamples to 4
  samples; no BLOCK expected.
- **Result** (`policy-run-20261013`):
  - 132/132 checks PASS, 7/7 cases;
  - 0 UNSTABLE, no commentary flip vs v2, so **no resampling was triggered**;
  - no contamination;
  - 30/30 regression tests; grader controls 3/3 agree;
  - $2.95.
- **Diff vs v2** (`compare_runs.py`): only case a S17/S18, **matching the prediction**.
- **Both SKILL.md rules were followed in this run.** Case b states zeros as observations and defers to the reviewer;
  case g names TTM, YoY and the 9-month span. That is one sample each.
- **Not exercised:** the resampling path itself ran only in unit tests (`test_policy.py`), never in a live run.
- **Baseline v3** = verbatim copy in `evals/baseline/policy-run-20261013/` (166 files, fingerprint in `BASELINE.md`).
  v2 moved to `evals/baseline/history/v2/`, and `current.json` now points to v3.
- **Committed run records:**
  - `commit5-run` (an honest FAIL, with NOTE.md);
  - the case b before/after runs (summary plus commentary);
  - the case g re-grades;
  - both prediction files.
- **Eval spend to date: $22.99.**

  | Item | Cost |
  |---|---:|
  | first-run | $2.73 |
  | v1 clean-run | $2.74 |
  | v2 commit3-run | $3.04 |
  | commit4-run | $2.99 |
  | commit5-run | $2.96 |
  | policy-run | $2.95 |
  | case b ×10 | $5.18 |
  | case g re-grades | $0.07 |
  | deleted smoke/probe runs | $0.33 |

  Since the case g decision: ≈ $3.02, against the $10 budget.

### D-53: Incident: fragments of the local secrets database printed into the session output
- **What happened (2026-10-13, before the commit-6 secret scan):**
  - I wrote an ad-hoc Python diagnostic, not the repo's scanner, to check the files to be committed against the
    values in `connection/.secrets/`.
  - To explain a false positive, it printed the 30 characters preceding each match inside
    `connection/.secrets/db.sqlite3`. That was three snippets of raw database bytes.
  - The match itself was a plain date (`YYYY-MM-DD`), so the scan result was a false positive. The snippets were
    the leak.
- **What was exposed, and where:**
  - Three fragments of up to 30 characters each, from `db.sqlite3`. They are not complete values.
  - They appeared only in the Claude Code session output. That means the local session transcript under
    `~/.claude/projects/` and the conversation sent to the model API.
  - **Nothing was committed or written to a repo file.** The commit-6 scan of 390 files was clean, and none of the
    real values in `backend.env` or `mcp-server.env` appears in any committed file.
  - I did not inspect the database to identify the fragments; that would have repeated the exposure.
- **Risk:**
  - **Most likely candidates:** the tail of a Django session row, or the tail of Fernet-encrypted token ciphertext
    (Fernet tokens end in `=`, which the diagnostic's regex keyed on).
  - **Session fragment:** low risk, since it's partial. But a session key or signature is a live credential while
    the session lasts.
  - **Ciphertext fragment:** no practical risk. Fernet ciphertext, even complete, is useless without `FERNET_KEY`,
    and that key was never printed.
- **What was rotated** (`connection/scripts/rotate_django_secret`, which prints counts and booleans only):
  - All Django sessions were deleted (6 rows), so every browser must log in again.
  - A new `DJANGO_SECRET_KEY` was written in place into `connection/.secrets/backend.env`. The value was never
    printed, and no `SECRET_KEY_FALLBACKS` were kept, so anything signed with the old key is invalid.
  - Verified in a fresh process: the new key is loaded and differs from the old one; 0 sessions remain; 0 of the old
    session keys load. `manage.py check` is clean, and the 63 backend tests pass.
- **Deliberately not rotated:**
  - The QuickBooks tokens and `FERNET_KEY`. The stored tokens are Fernet-encrypted, the key was not exposed, and
    fragments of ciphertext are useless without it.
  - Rotating the Intuit tokens would also break the read-only MCP setup for no security gain.
- **Fix (the cause was an ad-hoc diagnostic, not the scanner):**
  - **`connection/scripts/secret_scan`:**
    - Anything found in, or taken from, a `.secrets/` directory is reported as path, line or byte offset, and rule
      only: no fingerprint, no excerpt.
    - Binary files inside `.secrets/` (the SQLite database) are now scanned by offset.
    - A new known-value check compares scanned files with the real values in `.secrets/*.env` and reports
      `known-secret:<KEY>` with no value. It's on by default when the folder exists, so the pre-commit hook
      now runs it too. This is the check I had improvised, done safely.
  - **`connection/scripts/guard_secrets_hook.py`:** a Claude Code PreToolUse hook. It blocks any tool call whose
    path or command names `.secrets` (shell, Read, Edit, Write, Grep, Glob), so an ad-hoc diagnostic can't open
    the secret files.
    - Vetted tools that locate the folder themselves and print no values are unaffected: Django, `secret_scan`,
      and `rotate_django_secret`.
    - **Verified live** in a throwaway `claude -p` run with the hook loaded via `--settings`: `ls connection/.secrets`
      was blocked, and no file names were returned.
    - **Wiring it into `.claude/settings.json` was refused by Claude Code's own self-modification guard when I
      tried**, which is the right default. The user adds that file.
    - Limits: it guards against accidents, not a determined bypass (a path built at runtime isn't seen), and it
      fails open if Python can't start.
    - Once wired, eval skill runs (`claude -p` from the repo root) also load the hook. The skill never touches
      `.secrets`, so no eval change is expected. The suite wasn't re-run for this.
- **Tests:**
  - `connection/scripts/test_secret_scan.py`, 17 tests (4 new):
    - a planted fake secret in a `.secrets/backend.env` is reported as `backend.env:2  rule=...`, with no value, no
      6-character fragment of it, no fingerprint and no neighbouring text;
    - the same for a fake SQLite file, by byte offset;
    - a planted fake realm ID found in another file is reported by the known-secret rule, naming the key `QUICKBOOKS_REALM_ID` but not its value;
    - a clean file stays clean.
  - `connection/scripts/test_guard_secrets_hook.py`, 6 tests: the incident's exact pattern is blocked; shell and
    file tools on `.secrets` paths are blocked; vetted tools and look-alike names are allowed.
- **Lesson:** to look for secrets, use the scanner, never a one-off script. The scanner's no-value guarantee is
  tested; a one-off script's isn't.

### D-54: Skill change: no client figure in SKILL.md; reports record the workbook's file name only
- **SKILL.md style example.**
  - "Usage Fees fell 6.3% to 166,782" was a real ABC sandbox figure (`Income Statement!C11`). It now reads
    "Widget Rentals fell 4.2% to 12,340" (an invented example). I checked that the line name and the number appear
    in neither workbook.
  - Why: the rule in `CLAUDE.md` and `docs/ARCHITECTURE.md` is no client data or figures in skills.
  - The other examples were checked too:
    - The zero-line example's "2,500" coincides with two ABC cells, but not with that line or month, so it is
      effectively invented. Left as is.
    - **Eval leakage, fixed in a follow-up commit.** The TTM example, "the export covers only 9 months (Jan–Sep
      2026)", was exactly the span of the synthetic Bluebird workbook, which is **case g's input**. So the skill's
      own instructions contained the sentence case g's R1 rewards, which could inflate R1. It came in with the D-51
      TTM rule, and baselines v3 (`policy-run-20261013`) and earlier R1 passes after D-51 should be read with that
      in mind.
    - It now reads "the export covers only 7 months (Mar–Sep 2025)". Checked with the extractor: it matches neither
      workbook's span. ABC is Jan 2025–Jun 2026 (18 months), and Bluebird is Jan–Sep 2026 (9 months).
    - The v4 run (D-55) is the first measurement of R1 without the leak.
- **Report header and JSON.** `meta.source_file` is now the file name only, not the path passed in. That covers both
  the JSON contract and the Markdown header ("Generated … from `<file>`").
  - Before, a run on an absolute path recorded it in full, including the Windows user folder. Seen in the D-53
    fresh-clone check.
  - Test: `test_outputs_record_file_name_not_absolute_path` (31 skill tests). It fails without the fix.
- **Committed outputs checked:**
  - `trend-reports/` records the relative path `data\ABC Inc - ….xlsx`: no absolute path, no user folder. Not
    changed.
  - The skill outputs inside the eval baselines are also clean.
  - **Historical eval run records** do contain absolute paths, including the Windows user folder name. They appear
    in `skill_run/stream.jsonl` (21 files, Claude Code's own transcript of the working directory and tool calls)
    and `skill_run/run_meta.json` (2 files), across `evals/baseline/` and the committed run records. **Left
    unchanged** as historical records.
  - New harness runs will still record them, because the harness stores Claude Code's transcript; this skill
    change doesn't affect that.
- **Expected eval effect:**
  - None on structured checks (no golden reads `source_file`).
  - Commentary may differ only through the style example.
  - Verified by the v4 run (D-55).

### D-55: Full run after the skill-environment changes; baseline v4
- **Why a run:** the skill's environment changed in five ways:
  - `CLAUDE.md` (loaded by eval skill runs, which start in the repo root);
  - the `.secrets` guard hook in `.claude/settings.json` (D-53);
  - the invented style example (D-54);
  - the de-leaked TTM example (D-54);
  - reports naming the workbook file only (D-54).
- **Hook verified first:** a fresh `claude -p` started in the repo root, with no `--settings` flag, had
  `test -d connection/.secrets` blocked by the hook, with the D-53 message and no file names returned.
  - Allowed calls leave no trace in the transcripts, so the eval runs can't show the hook firing.
  - The harness starts `claude -p` the same way (repo root, no `--setting-sources` override).
- **Prediction, written before the run** (`evals/baseline/v4-run-20261013.prediction.txt`, 2026-10-13T03:19:00Z):
  - the same 132 check ids, with no deterministic verdict change;
  - commentary may differ, with case g R1 the most likely to move;
  - no BLOCK.
- **Result** (`v4-run-20261013`):
  - **132/132 PASS, 7/7 cases, 0 UNSTABLE**, no commentary flip, so no resampling;
  - no contamination; 31/31 regression tests; grader controls 3/3;
  - **$3.05**.
  - `compare_runs.py` against v3 finds **no difference**, which matches the prediction.
- **Case g without the leak:** the commentary still says "TTM and year-over-year comparisons can't be computed,
  because the export covers only 9 months (Jan–Sep 2026)". Its figures now come from the data, not from an example
  in the instructions, and R1 passed.
  - That is **one sample**: it shows the rule works without the leaked sentence, not a pass rate.
- **Seen in passing:** in case a the skill tried an unapproved PowerShell process listing, which Claude Code's
  permission check denied (not the hook). Earlier baselines had 4 such denials, so this isn't new, and the case
  passed.
- **Baseline v4** = verbatim copy in `evals/baseline/v4-run-20261013/` (166 files; fingerprint in `BASELINE.md`).
  v3 moved to `evals/baseline/history/v3/`, and `current.json` now points to v4.
- **Spend:** this run cost $3.05. Plus $0.02 of `claude -p` checks: the hook tests ($0.003 each) and the fresh-clone
  skill run ($0.012).
  - Eval spend to date: **$26.04** ($22.99 + $3.05).

### D-56: `submission/`: generated, examiner-facing response files (extras branch)
- **What:** `submission/` holds one easy-to-read file per task. All of them are generated by
  `scripts/build_submission.py` from outputs that already exist, so the folder adds no new logic and no new test
  cases.
  - `Task 1 response.md` comes from the smoke test's redacted evidence. It's live: `--live-task1`.
  - `Task 2 response.md` is the newest complete skill report, with a header.
  - `Task 3.1.md`–`Task 3.7.md` map to golden cases a–g.
  - `Task 3 response.md` summarises the latest eval run; by default that's the current baseline.
- **Commands:**
  - **Free:** `python scripts/build_submission.py`. No network, no Claude, no QuickBooks call.
  - **Live, Task 1 only:** `--live-task1`. Free, no Claude call, but a real sandbox query.
- **Replacement rule:** every file is replaced atomically (temp file, then rename), and only when its inputs are
  valid; otherwise the previous file stays.
- **Single sources of truth:** `evals/goldens/cases.json` and `source_facts.json` for the case files, the run's
  `results.json` for the summary, and the skill's own report for Task 2. Reused rather than duplicated:
  `run_evals.fmt_fact` and `GRADER_MODEL`, `compare_runs.main` (its output is captured), the grader rules from
  `grader_prompt.md`, and the known limits from `evals/README.md`.
- **Drift test:** `evals/tests/test_submission_docs.py` (13 tests; eval-side total 53) fails if any `Task 3.N.md`
  no longer equals a fresh render of `cases.json`, or if a case file is missing or extra. Shown to fail on a
  one-character edit.
  - It also checks:
    - pass rates count only executed checks;
    - the summary total equals the run score;
    - Task 2 never uses an incomplete report or downgrades to an older one;
    - Task 1 rejects failed runs, never writes more than 4 realm characters, explains a Django skip, and keeps the
      previous file on failure.
- **Summary sections:** `Task 3 response.md` reports results separately:
  - execution, 42/42;
  - numeric, 20/20 (value and count checks against raw-cell facts);
  - reconciliation, 8/8 (`data_quality` checks);
  - report content, 27/27;
  - provenance, 7/7;
  - commentary, 28/28.

  These add up to the run's 132.
- **`smoke_test` evidence field:** the smoke test now records `net_income_latest_complete_month` in its evidence
  JSON. That is the newest month column covering a whole calendar month that ended before today; the partial
  current month and the Total column are skipped.
  - It is recorded inside the existing P&L check, so the check count stays 11.
  - No change to OAuth, token handling, the launcher, the hook or `.mcp.json`.
  - **Live run (2026-10-13 15:01 UTC):** 10 passed, 1 skipped (the Django `/test` check: checked out to MCP and
    Django's cached access token expired, by design per D-16), 0 failed. Sep 2026 net income was 1,680.78.
  - The "Why one check was skipped" sentence was added to the generator after that run. It was inserted once into
    the existing `Task 1 response.md` using the generator's own text, not by re-running the live query.
- **Task 2 cause wording, kept by decision:**
  - The chosen report (`demo-output/abc-inc-2026-06-trends.md`, 2026-10-13 04:06 UTC) says the negative Mar 2026
    months in Partnership Income and White-Label are "likely credits or refunds; reviewer to confirm".
  - That wording comes from the engine's own hedged flags ("likely credits/refunds; reviewer to confirm"), which
    the commentary repeats. It is deferred to the reviewer, so it stays within F2 ("framing it as … 'reviewer to
    confirm' is allowed").
  - The other causal-sounding phrases are arithmetic attribution, not outside causes: "which drove Finance & Admin"
    and "only because of non-operating items".
  - The report was kept, not regenerated. Removing the phrase from the flags would be an engine change.

### D-57: Audit fixes: example report, Task 2 provenance, QUICKSTART, a discrimination check, and a P1 defect
- **Stale example replaced.**
  - `trend-reports/abc-inc-2026-06-trends.{md,json}` came from the engine before D-45/D-48. Its flags still said
    "SKU Profiling is zero in Jun 2026", which case a's S18 now forbids.
  - Both files were replaced with the current report (generated 2026-10-13 04:06 UTC, current engine, commentary
    written by Claude, model not recorded). It is the same report `submission/Task 2 response.md` was built from.
  - The skill, the engine and the goldens are unchanged.
- **Task 2 source can now be checked from the repo.** `scripts/build_submission.py` looks only at the committed
  `trend-reports/` (`TASK2_SOURCES`); the git-ignored `demo-output/` is no longer a source. `submission/` was
  rebuilt (Task 2 now cites `trend-reports/abc-inc-2026-06-trends.md`), and the drift test passes.
- **QUICKSTART:** "expect 11 passed" became "11 passed, or 10 passed + 1 skipped once Django's cached token has
  expired (by design, D-16)".
- **Discrimination check** (`evals/DISCRIMINATION_CHECK.md`, $0.17, 5 grader calls):
  - Copies of v4 outputs, kept outside the repo, were graded with the existing, unmodified grading functions.
  - Breaks and what caught them:
    - wrong Jun 2026 revenue: **S2**, plus grader **R1** and **F4**;
    - "permanently discontinued": case b **F2**;
    - invented cause: case a **F2**;
    - made-up TTM figure: case g **F1**.
  - The clean copy passed: 18/18 structured, P1 PASS, 9/9 commentary.
- **Defect found, not fixed: P1 cannot fail in harness runs.**
  - The harness calls `provenance.check(commentary, analysis, md)` with the full report. The commentary lives
    inside that report, so each commentary number matches itself. The made-up TTM figure passed P1.
  - D-44's planted-number test missed this because it passed a report that did not contain the planted text.
  - So the P1 PASS in every recorded run (v1–v4) is **not evidence** of number provenance. The structured checks
    and the grader are unaffected.
  - Demonstrated fix: match against the report with the commentary section removed. Then the made-up figure fails
    P1 and the clean copy still passes.
  - Not applied: this change set excluded harness changes. Applying it needs a harness change plus a test, and a
    rerun would set a new baseline.
- **Also:** `connection/DECISIONS_SUMMARY.md` (the 10 most important decisions on one page) is linked from the top
  of this log and from the README. The P1 standalone example in `evals/README.md` now points at the current baseline
  (the old path had moved to `history/v1`).
- **Not done here:** making the GitHub repo private. `gh` is not installed, so it has to be done in the web UI.

### D-58: P1 fixed: the commentary can no longer vouch for its own numbers; baseline v5
- **Defect (found by D-57's discrimination check):**
  - The harness calls `provenance.check(commentary, analysis, md)` with the full report, and the skill writes its
    commentary into that report. So every commentary number matched itself, and P1 could not fail.
  - The check's break (d), "TTM revenue is 1,234,567" added to case g, passed P1.
  - D-44's planted-number test missed this because it passed a report that did not contain the planted text.
- **Fix** (`evals/provenance.py`, `without_commentary`): P1's pool is the run's JSON plus the report with the
  commentary removed.
  - The commentary is the text between `## 1. Commentary (draft)` and the engine's `### Flags raised`, plus any
    report line identical to a commentary line.
  - Whole lines only. A first version also removed verbatim substrings, and the existing test
    `test_report_text_counts_as_output` caught it: that removed engine prose which merely contained a commentary
    phrase. The engine's flags and tables stay in the pool.
  - No ignore rule, golden or tolerance was changed.
- **Tests:** `test_provenance.py::CommentaryCannotVouchForItself` (4 tests; eval-side total 57):
  - break (d) rebuilt on the current baseline and called exactly as the harness does: FAIL, with exactly
    `1,234,567` unmatched;
  - the clean case a: PASS;
  - every current baseline case: PASS;
  - engine text still counts as a source.

  Without the fix, the old P1 passes break (d) (checked with the fix stashed).
- **Re-check of history with the fixed P1:** all 7 cases of each of v1, v2, v3 and v4 PASS, with 0 unmatched. The
  earlier P1 PASSes were unproven, not wrong.
- **Discrimination check re-run** ($0.16, `evals/DISCRIMINATION_CHECK.md`): the same verdicts as before, except
  break (d) is now caught by **P1** as well as grader F1. The clean copy still passes.
- **Prediction, written before the run** (`evals/baseline/v5-run-20261013.prediction.txt`): the same 132 checks;
  no deterministic change; P1 PASS on all 7 cases (the risk being a fresh commentary citing a number the engine
  didn't produce); no BLOCK.
- **Result** (`v5-run-20261013`):
  - **132/132 PASS, 7/7 cases, 0 UNSTABLE**, no flip, so no resampling;
  - no contamination; 31/31 regression tests; grader controls 3/3;
  - **$2.90**.
  - P1, now a check that can fail: 0 unmatched in every case (a 52, b 40, c 49, d 43, e 51, f 39, g 50 matched).
  - `compare_runs.py` against v4 finds **no difference**, which matches the prediction.
- **Baseline v5:** a verbatim copy in `evals/baseline/v5-run-20261013/` (166 files; fingerprint in `BASELINE.md`).
  v4 moved to `history/v4/`, and `current.json` now points to v5.
- **Removed:** the "P1 cannot fail" caveat in the submission generator, `submission/` and `evals/README.md`.
  DECISIONS_SUMMARY now points here.
- **Spend:** this change cost $3.06 ($0.16 for the check, $2.90 for the run). Eval spend to date: **$29.27**.
