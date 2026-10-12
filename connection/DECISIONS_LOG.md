# Decisions log: Task 1 (QuickBooks Online ↔ Claude)

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
