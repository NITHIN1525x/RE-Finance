# Troubleshooting: QuickBooks sandbox ↔ Claude

Each entry gives the symptom, the cause, and the fix. Messages in `code` are the exact text this
project shows. Run commands from `connection/backend` with the venv's Python
(`.venv\Scripts\python` on Windows, `.venv/bin/python` on POSIX) unless stated otherwise.

Quick health check from the repo root:
```powershell
connection\backend\.venv\Scripts\python connection\scripts\smoke_test --client abc-inc-sandbox
claude mcp list
```

---

## 1. Redirect URI mismatch
**Symptom:** after clicking **Connect QuickBooks**, Intuit shows an error page about the `redirect_uri`
instead of the consent screen. Or the console shows `Intuit rejected the authorization code. Check the
redirect URI and app keys.` (`reason=token_exchange_failed`).

**Cause:** the URI sent by Django (`QUICKBOOKS_REDIRECT_URI` in `connection/.secrets/backend.env`) doesn't
match a URI registered on the Intuit app **character for character**: scheme, host, port, path and
trailing slash all count. `localhost` and `127.0.0.1` are different URIs.

**Fix:** In the Intuit Developer Portal, open your app → **Settings → Redirect URIs**, in the
**Development** section. Register exactly `http://localhost:8000/api/qbo/callback`, then restart Django
if you changed `backend.env`. Use Development keys: production apps reject `http://localhost` redirect URIs.

> Don't also register `http://localhost:8000/callback` (the official server's own callback). Leaving it
> unregistered is deliberate (DECISIONS_LOG D-07).

## 2. Invalid OAuth state
**Symptom:** the console banner says `The authorization link was invalid, reused or opened in a
different session. Click Connect again.` (`reason=invalid_state`), or `...took longer than 10 minutes`
(`reason=state_expired`). The audit log shows `oauth_callback … Rejected: missing, mismatched or replayed
OAuth state`.

**Causes:**
- The console was opened as `http://127.0.0.1:5173`. The callback lands on `localhost:8000`, and cookies
  for `127.0.0.1` aren't sent to `localhost`, so the session holding the `state` is missing.
- More than 10 minutes passed between Connect and approving at Intuit.
- The Intuit tab was reused or refreshed after a callback had already run: `state` is single-use.
- You signed out, cleared cookies, or finished the flow in a different browser or profile.

**Fix:** open **http://localhost:5173** (not 127.0.0.1), sign in, and click **Connect QuickBooks** again.
Nothing is stored on a rejected callback.

## 3. Expired or rotated refresh token
**Symptom:**
- The card shows **Reconnect required**, or **Test connection** says `QuickBooks authorization expired or
  was revoked. Click Connect QuickBooks to re-authorize.`
- The audit log shows `refresh … Refresh token rejected; reconnect required`.
- On the MCP side, the server's stderr shows `Refresh token rejected (…); falling back to interactive OAuth`.

**Causes:**
- About 100 days without a refresh (rolling window).
- The 5-year maximum lifetime.
- The app was disconnected inside the QuickBooks company.
- **Two components refreshed the same token.** Intuit rotates the value roughly daily, and the one that
  didn't save the new value is left holding a dead token. This happens if someone ran upstream's
  `npm run auth`, copied a token by hand, or ran `sync_mcp_tokens --force` while a server was still running.

**Fix:**
1. If the card shows **Checked out to MCP**: exit every Claude Code session using this repo, then run
   `python manage.py sync_mcp_tokens --client abc-inc-sandbox`.
2. Click **Reconnect QuickBooks** in the console.
3. Re-run `python manage.py export_mcp_env --client abc-inc-sandbox` before using Claude again.

> The MCP server's interactive fallback cannot succeed here (its callback URI isn't registered, and
> Django holds port 8000). That is intended: re-authorization always goes through the console.

## 4. Wrong `.env` path
| Symptom | Cause | Fix |
|---|---|---|
| Django won't start: `DJANGO_SECRET_KEY is not set (expected in …backend.env or the environment)` | `connection/.secrets/backend.env` is missing | `python connection/scripts/init_secrets.py` (repo root), then fill in the Intuit keys |
| Console banner: `The Intuit app credentials are not configured on the server` | `QUICKBOOKS_CLIENT_ID`/`SECRET` empty, or written as `KEY = VALUE` with spaces | Edit `connection/.secrets/backend.env` (`KEY=VALUE`, no quotes), restart Django |
| `[mcp_launch] REFUSING TO START: no connection is checked out to the MCP server` | Nothing has been exported to the token store yet | `python manage.py export_mcp_env --client abc-inc-sandbox` |
| `[mcp_launch] REFUSING TO START: token store not found` | `connection/.secrets/mcp-server.env` deleted | `python connection/scripts/init_secrets.py`, then `export_mcp_env` |
| Upstream error `QUICKBOOKS_TOKEN_STORE_PATH must be an absolute path` | Server started without the launcher, with a relative path | Always start it through `connection/scripts/mcp_launch.mjs` (what `.mcp.json` does) |
| Edits to `connection/quickbooks-online-mcp-server/.env` have no effect | By design: the launcher points the server at `connection/.secrets/mcp-server.env` | Don't put credentials in the submodule's `.env` |

## 5. Port 8000 already in use
**Symptom:** `runserver` prints `Error: That port is already in use.`

**Find the owner (PowerShell):**
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Get-Process -Id $_.OwningProcess }
```
A common culprit is upstream's `npm run auth` or its interactive OAuth fallback, which also binds port
8000. Stop that process. **Don't move Django to another port** unless you also change the Intuit redirect
URI, `QUICKBOOKS_REDIRECT_URI` in `backend.env`, and the proxy target in `connection/frontend/vite.config.js`.
Port 5173 is pinned the same way (`strictPort`); if it's busy, Vite exits rather than picking another port.

## 6. MCP server not loading in Claude Code
Work through these in order:
1. **Wrong working directory.** Project servers come from the `.mcp.json` at the session's root. Start
   Claude Code in `E:\RE-Finance\qbo-claude-exercise`, not in a parent folder.
2. **Not approved.** If `claude mcp list` shows `⏸ Pending approval (run 'claude' to approve)`, start
   `claude` in the repo root and approve **quickbooks-sandbox**. If you declined earlier, reset with
   `claude mcp reset-project-choices`.
3. **Launcher refused.** Run `node connection/scripts/mcp_launch.mjs` from the repo root. A
   `REFUSING TO START: …` line says exactly what's wrong (store empty, environment not `sandbox`, flags
   not `true`, server not built, axios too old). If it prints a "starting" line instead, the launcher is
   fine; press Ctrl+C.
4. **Server not built or dependencies reverted.** In `connection/quickbooks-online-mcp-server`, run:
   `npm ci`, then `npm install --no-save --ignore-scripts axios@1.20.0` (required after **every** `npm ci`),
   then `npm ls axios`, then `npm run build`.
5. Inside Claude Code, run `/mcp` to see the status, or `/mcp reconnect all`. For slow starts, raise the
   startup timeout: `$env:MCP_TIMEOUT=30000; claude`.
6. **Large reports truncated or refused.** Claude Code caps MCP output at 25,000 tokens by default. A
   12-month by-month P&L is about 21k. Ask for shorter periods, or set `MAX_MCP_OUTPUT_TOKENS`.

## 7. CORS or Vite proxy issues
| Symptom | Cause | Fix |
|---|---|---|
| `Cannot reach the backend. Is Django running on port 8000?` | Django not running | Start it: `python manage.py runserver localhost:8000` |
| `The backend is not responding (is Django running?)` | The Vite proxy got no answer from :8000 | As above; check the Django console for a traceback |
| POST returns 403 / `Your session has expired. Please sign in again.` | Session expired (8 h), you signed out in another tab, or the `csrftoken` cookie was cleared | Reload the page (it re-fetches `/api/me/`, which re-issues the CSRF cookie) and sign in again |
| Everything works except **Connect** fails with `invalid_state` | Console opened via `127.0.0.1:5173` while the callback goes to `localhost:8000` (see §2) | Use `http://localhost:5173` |
| Browser console shows CORS errors | The UI was served without the Vite proxy and called `:8000` directly from another origin | Use `npm run dev` (proxy). Only `FRONTEND_URL` is allowed by CORS |
| `/api/...` returns the React page or 404 | Vite started without `vite.config.js` (wrong folder) | Run `npm run dev` inside `connection/frontend` |

## 8. Sandbox / production environment mismatch
| Symptom | Meaning |
|---|---|
| Django refuses to start: `QUICKBOOKS_ENVIRONMENT must be exactly 'sandbox'; production is refused by design` | `backend.env` has anything other than lowercase `sandbox` (including `Sandbox`) |
| `[mcp_launch] REFUSING TO START: QUICKBOOKS_ENVIRONMENT in the token store is not exactly "sandbox"` | Token store was edited by hand; re-run `export_mcp_env` |
| Console: `That company is not reachable on the sandbox API, so the connection was refused and revoked.` | The authorized company didn't answer on `sandbox-quickbooks.api.intuit.com` (e.g. Production keys or a real company). The new grant was revoked and nothing was stored |
| `Refusing QuickBooks API call to non-sandbox host` | The host allow-list blocked a non-sandbox URL before any network call |

Use the app's **Development** keys and a company from the portal's **Sandbox** menu.

## 9. Missing scopes or revoked authorization
**Symptoms and causes:**
- **Test connection** reports `QuickBooks refused access to this company (is it a sandbox company?)`
  (HTTP 403), or `QuickBooks rejected the access token` (401) persisting after one automatic retry.
- Refresh fails with `invalid_grant`: the app was disconnected from inside the QuickBooks company
  (Apps → manage apps → Disconnect), or the Intuit app was deleted, or its keys were rotated.
- `Intuit rejected the app credentials (check client ID/secret)`: wrong keys, or Production keys used
  against a sandbox flow.

**Scope:** only `com.intuit.quickbooks.accounting` is requested. Make sure the Intuit app has the
Accounting scope enabled. There is no read-only accounting scope at Intuit; read-only is enforced by the
MCP restriction flags (DECISIONS_LOG D-09/D-25).

**Fix:** Disconnect in the console (it wipes local tokens even if the revoke fails), then
**Connect QuickBooks** again.

---

## Expected behaviours that look like errors
- **`Test connection` returns 409 `checked_out`** about an hour after `export_mcp_env`. While the MCP
  server owns the token, Django won't refresh it (single owner, D-16). Exit Claude Code, run
  `sync_mcp_tokens`, and the button works again.
- **`sync_mcp_tokens` says `MCP server appears to be running`.** Exit every Claude Code session for this
  repo, or disable the server in `/mcp`, then retry. `--force` skips the check: use it only if you are
  sure nothing is running.
- **`search_accounts` with `count: true` fails** (HTTP 400, an upstream issue). Count accounts from the
  full list instead. Customer and vendor counts work.
- **`npm audit` still lists axios 1.19.0** after the patch: it reads the lockfile. Verify with `npm ls axios`.
