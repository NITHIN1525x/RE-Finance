# Five-minute live demo: QuickBooks sandbox ↔ Claude

**Story:** a firm connects a client's QuickBooks once, through a console that keeps tokens encrypted
and audited. Claude then answers questions from that company's data through the official Intuit MCP
server, read-only and sandbox-only. Every number Claude gives can be traced to a tool call.

---

## Before the demo (about 10 minutes beforehand, not on screen)

```powershell
# Terminal A: backend
cd E:\RE-Finance\qbo-claude-exercise\connection\backend
.venv\Scripts\python manage.py runserver localhost:8000

# Terminal B: frontend
cd E:\RE-Finance\qbo-claude-exercise\connection\frontend
npm run dev

# Terminal C (repo root): make sure Django owns the token at the start, then run a health check
cd E:\RE-Finance\qbo-claude-exercise
connection\backend\.venv\Scripts\python connection\backend\manage.py sync_mcp_tokens --client abc-inc-sandbox   # skip if not checked out
connection\backend\.venv\Scripts\python connection\scripts\smoke_test --client abc-inc-sandbox --skip-django
```
- If `smoke_test` reports `no connection is checked out`, that's expected after a sync, so skip it. Run
  it after step 3 instead.
- Have a browser on **http://localhost:5173**, signed in as `nithin`, and a terminal open in the repo
  root for Claude Code.
- Keep `connection/evidence/phase5_ground_truth.md` open in a tab. It is the answer key.

---

## The demo

### 0:00–0:45: The Connection Console
- Point at the **SANDBOX** badges: the backend refuses to start for anything else, and every API call
  is pinned to `sandbox-quickbooks.api.intuit.com`.
- The client card shows:
  - realm `9341…`: only the first four characters ever leave the backend;
  - **Connected** status;
  - last refresh time;
  - token expiry (refresh token about 100 days and rolling; access token 60 minutes).
- **Recent activity:** each OAuth step, refresh and test is audited with who, when, which client, which
  action and the result. No token values appear.

### 0:45–1:30: Test connection
- Click **Test connection** and show the company name **Sandbox Company US 1bad** and the 12-month P&L summary.
- Optional: open DevTools → Network → the `test` response. It holds a summary only. No tokens exist
  anywhere in the browser (session is an HttpOnly cookie).

### 1:30–2:00: Hand the connection to the MCP server (one token owner at a time)
```powershell
connection\backend\.venv\Scripts\python connection\backend\manage.py export_mcp_env --client abc-inc-sandbox
```
- Refresh the console: the card shows **Checked out to MCP**. Django has refreshed for the last time
  and now refuses to, because Intuit rotates refresh tokens and two refreshers would strand each other.

### 2:00–4:00: Ask Claude
```powershell
cd E:\RE-Finance\qbo-claude-exercise
claude
```
1. Run `/mcp`. It should show **quickbooks-sandbox** connected with **71 tools**, all read-only
   (no `create_`, `update_` or `delete_` tools).
2. Ask: **"What was net income in the sandbox last quarter, and what were the top three expense accounts?"**
3. Show the tool call Claude makes (`get_profit_and_loss` with `start_date 2026-07-01`,
   `end_date 2026-09-30`), then the answer.
4. **Grounding:** compare with `phase5_ground_truth.md`. Net income should be **1,585.21** (income
   9,809.52; COGS 405.00; expenses 4,903.31; other expenses 2,916.00).

**What a good answer includes:**
- States the period it chose: "last quarter" = **Q3 2026, Jul 1 to Sep 30**. The fiscal year starts
  in January, so calendar and fiscal quarters match. It should also give the accounting basis (accrual).
- Net income **1,585.21**, taken from the report, not recomputed loosely.
- Says what "top three expense accounts" means. The answer changes with the definition:
  - Top-level *Expenses* accounts: Job Expenses 957.89, Maintenance and Repair 940.00, Rent or Lease 900.00.
  - Individual (leaf) accounts: Rent or Lease 900.00, Equipment Repairs 755.00, Accounting 640.00.
  - **Miscellaneous 2,916.00** sits under *Other Expenses* and is the largest single cost. A good answer
    flags it rather than silently dropping or including it.
- Names the tool or report it used, and doesn't produce figures the tools didn't return.

**When data is missing or unsupported:**
- A month with no activity should come back as "no activity / 0 in the report", never an estimate.
- If a tool returns text starting with `Error`, Claude should say the call failed. Example: counting
  accounts with `count: true` fails with HTTP 400 upstream, so it should use the account list instead.
- If a report is too large (a 12-month by-month P&L is about 21k tokens, against Claude Code's 25k
  cap), ask for shorter periods rather than trusting a truncated result.
- If asked for something no tool provides (budget vs. actual by department, for example), Claude
  should say so.

5. **Show a write is impossible:** ask *"Create a customer called Demo Test."* Claude should reply that
   no create, update or delete tool is available. No QuickBooks request is made, because those tools
   were never registered (`QUICKBOOKS_DISABLE_*=true`, checked by the launcher).
   Verified (Run 3 in `evidence/phase5_claude_runs.md`): Claude made only read lookups, refused both
   writes, and explained the server is read-only. It *suggested* enabling write tools as an option, so
   say clearly that read-only is a deliberate choice.

### 4:00–4:30: Hand the token back
Exit Claude Code (`/exit`), then:
```powershell
connection\backend\.venv\Scripts\python connection\backend\manage.py sync_mcp_tokens --client abc-inc-sandbox
```
- If the server rotated the refresh token, the new one is stored encrypted, and the console's
  **Test connection** works again.
- If Claude Code is still running, the command refuses. That's intentional: two live owners of one
  rotating token.

### 4:30–5:00: Honest limits
- This is a single-laptop design: stdio MCP, SQLite, `runserver`, and session login without SSO.
- Read-only is a tool-registration control. Intuit's accounting scope itself allows writes.
- For a team: containerised Django plus one MCP instance per client behind authenticated Streamable
  HTTP, a secrets manager, and PostgreSQL. See `CONNECTION.md`.

---

## Three likely live-modification requests

### 1. "Show year-to-date instead of the last 12 months in Test connection"
- **Backend:** `connection/backend/qbo/reports.py`. Add a `year_to_date()` helper next to
  `last_12_months()`, and use it in `test_connection` in `connection/backend/qbo/views.py` (the
  `start, end = reports.last_12_months()` line).
- **Frontend:** nothing needs to change. `TestResult.jsx` prints `start_date`/`end_date` from the response.
- **Verify:**
  `cd connection/backend; .venv\Scripts\python manage.py test qbo --settings=config.settings_test`,
  then click **Test connection**. `runserver` reloads automatically.

### 2. "Add a second client company"
```powershell
cd E:\RE-Finance\qbo-claude-exercise\connection\backend
.venv\Scripts\python manage.py create_client --name "XYZ Ltd (sandbox)" --slug xyz-sandbox --member nithin
```
- Refresh the console and click **Connect QuickBooks** on the new card. Pick a **different** sandbox
  company: one company can belong to only one active client, so the same one is refused with
  `realm_in_use`.
- Point out that only one client can be checked out to the local MCP server at a time. Running
  `export_mcp_env --client xyz-sandbox` while ABC is checked out is refused, which keeps a Claude
  session bound to exactly one company.

### 3. "Show the balance sheet total in Test connection too"
- **Backend:** in `test_connection` (`connection/backend/qbo/views.py`), add a call
  `intuit.api_get(conn.realm_id, "reports/BalanceSheet", access_token, {"end_date": end.isoformat()})`.
  In `connection/backend/qbo/reports.py`, add a `summarize_balance_sheet()` that reads the
  `TotalAssets` and `TotalLiabilitiesAndEquity` summary rows (same pattern as `summarize_pnl`), and
  return it as `"balance_sheet"`.
- **Frontend:** in `connection/frontend/src/components/TestResult.jsx`, add two rows that render
  `result.balance_sheet`.
- **Test:** extend `FakeIntuit.get` in `connection/backend/qbo/tests/helpers.py` to answer
  `/reports/BalanceSheet`, and add an assertion in `test_tokens_and_disconnect.py`. Expected sandbox
  value today: total assets **23,436.29**.

**Request to decline live: "let Claude create an invoice for the demo".** That would mean removing the
read-only checks in two places (`connection/backend/qbo/mcp_store.py` `READ_ONLY_FLAGS` and
`connection/scripts/mcp_launch.mjs`). It's a deliberate security decision, not a demo tweak.
