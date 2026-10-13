# Task 1 quick start: connect the QuickBooks sandbox to Claude

Commands run from the repo root unless a step says `cd`. Back to the [submission index](../README.md).


About 10 minutes once the prerequisites are in place. Commands are PowerShell; POSIX differences are
noted inline.

**Prerequisites:**
- Git, Node 22+, Python 3.12+, Claude Code.
- An Intuit developer account with an app and a **sandbox company**.
- On that app: **Settings → Redirect URIs (Development)** set to exactly
  `http://localhost:8000/api/qbo/callback`, and nothing else is needed. Don't add upstream's
  `http://localhost:8000/callback`.

## 1. Clone and protect
```powershell
git clone --recurse-submodules <this-repo> qbo-claude-exercise
cd qbo-claude-exercise
git config core.hooksPath .githooks          # secret-scanning pre-commit hook
python connection/scripts/init_secrets.py    # creates connection/.secrets/ (owner-only) + generated keys
```
Open `connection/.secrets/backend.env` and fill in `QUICKBOOKS_CLIENT_ID=` and
`QUICKBOOKS_CLIENT_SECRET=` with the app's **Development** keys. Write them as `KEY=VALUE`, with no
spaces and no quotes. This is the only file where a human types credentials.

## 2. Build the official MCP server, including the REQUIRED axios patch
```powershell
cd connection/quickbooks-online-mcp-server
npm ci
npm install --no-save --ignore-scripts axios@1.20.0   # REQUIRED after EVERY npm ci, not a one-off
npm ls axios                                          # must show axios@1.20.0 on every path
npm run build
cd ../..
```
**Why the extra line:** the pinned lockfile installs axios 1.19.0, which has 12 advisories. The
`--no-save` install upgrades `node_modules` only, so the pin stays faithful. Any later `npm ci` silently
reverts it, and `npm audit` keeps listing 1.19.0 because it reads the lockfile, so check with
`npm ls axios`. The launcher refuses to start the server if axios is older than 1.20.0. See
[D-04](DECISIONS_LOG.md).

## 3. Backend
```powershell
cd connection/backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # POSIX: .venv/bin/python
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser --username <you>      # you choose the password (12+ chars)
.venv\Scripts\python manage.py create_client --name "ABC Inc (sandbox)" --slug abc-inc-sandbox --member <you>
.venv\Scripts\python manage.py runserver localhost:8000              # leave running (terminal A)
```

## 4. Frontend (terminal B)
```powershell
cd connection/frontend
npm ci --ignore-scripts
npm run dev                                  # http://localhost:5173 (use "localhost", not 127.0.0.1)
```

## 5. Connect the sandbox company (browser)
1. Open **http://localhost:5173** → **Sign in**.
2. Click **Connect QuickBooks** on the client card, approve your sandbox company at Intuit, and you land
   back on the console with a "connected" banner.
3. Click **Test connection** to see the company name and the 12-month P&L summary.

## 6. Hand the connection to the MCP server and use Claude
```powershell
cd connection/backend
.venv\Scripts\python manage.py export_mcp_env --client abc-inc-sandbox   # MCP server now owns token refresh
cd ../..
claude                                       # start Claude Code IN the repo root; approve "quickbooks-sandbox"
```
- In Claude Code, run `/mcp`. You should see **quickbooks-sandbox: connected, 71 tools**.
- Try asking *"What was net income in the sandbox last quarter, and what were the top three expense
  accounts?"*

## 7. Verify, and hand back when done
```powershell
connection\backend\.venv\Scripts\python connection\scripts\smoke_test --client abc-inc-sandbox   # expect 11 passed
# after exiting Claude Code:
connection\backend\.venv\Scripts\python connection\backend\manage.py sync_mcp_tokens --client abc-inc-sandbox
```

## Tests
```powershell
cd connection/backend; .venv\Scripts\python manage.py test qbo --settings=config.settings_test   # 63 tests
cd ../..; python connection/scripts/test_secret_scan.py                                       # 17 tests
python connection/scripts/test_guard_secrets_hook.py                                          # 6 tests
python connection/scripts/secret_scan --all
cd connection/frontend; npm run build; npm run lint
```
