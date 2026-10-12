# Phase 5 evidence: ground truth vs. Claude's answers

These are sandbox figures from **Sandbox Company US 1bad** (realm `9341…`), captured 2026-10-12.

**Ground truth** came from calling the same MCP tools directly through `connection/scripts/mcp_launch.mjs`
(the command `.mcp.json` uses), parsing the raw JSON in code, with no model involved. **Claude** means the
`claude -p` runs in `phase5_claude_runs.md`. Raw outputs stay in `evidence/raw/` (git-ignored).

## Data checks (Run 1)

| Check | Ground truth (direct tool call) | Claude (Run 1) | Verdict |
|---|---|---|---|
| Company | `get_company_info`: Sandbox Company US 1bad, US, fiscal year starts January | same | ✅ |
| Sandbox evidence | Launcher refuses unless `QUICKBOOKS_ENVIRONMENT=sandbox`; API host `sandbox-quickbooks.api.intuit.com` (Django check) | Name pattern only; said no QBO field states "sandbox" | ✅ Honest. The proof lives in our config, not in the data |
| Chart of accounts | `search_accounts {fetchAll:true}`: 89 (active only, the default filter) | 90 = 89 active + 1 inactive (`Active=false` search) | ✅ More complete than my first ground truth |
| Customers | `search_customers {count:true}`: 29 | 29 | ✅ |
| Vendors | `search_vendors {count:true}`: 26 | 26 | ✅ |
| Inactive customers/vendors | `count:true` + `Active=false` filter: HTTP 400 | reported the 400 and declined to guess | ✅ Disclosed |
| P&L, 2025-11-01 → 2026-10-12, by month | Net income: May 91.25, Jul 863.87, Aug -959.44, Sep 1,680.78, Oct 1–12 -34.00, other months 0; total **1,642.46**. Income 10,200.77; COGS 405.00; Expenses 5,237.31; Other expenses 2,916.00 | identical | ✅ |
| Balance sheet as of 2026-10-12 | Total assets **23,436.29** = total liabilities and equity 23,436.29 | Assets 23,436.29; liabilities 31,131.33; equity -7,695.04 (sum 23,436.29) | ✅ |
| Write tools available | 0 of 71 registered | "None" | ✅ |

## Demo question (Run 2): "net income last quarter, top three expense accounts"

Ground truth: `get_profit_and_loss {start_date: 2026-07-01, end_date: 2026-09-30}`

- **Net income Q3 2026: 1,585.21.** Income 9,809.52; COGS 405.00; Expenses 4,903.31; Other expenses 2,916.00.
- The **top three depend on the definition**, and a good answer should say which one it used:

| Definition | #1 | #2 | #3 |
|---|---|---|---|
| Top-level accounts in the *Expenses* section | Job Expenses 957.89 | Maintenance and Repair 940.00 | Rent or Lease 900.00 |
| Leaf (posting) accounts, *Expenses* section | Rent or Lease 900.00 | Equipment Repairs 755.00 | Accounting 640.00 |
| Including *Other Expenses* | Miscellaneous 2,916.00 | (then as above) | |

Claude's answer: 1,585.21, a table for each definition, the parent/leaf distinction noted, Miscellaneous
flagged, and subtotals reconciled to the report. ✅ All figures match.

## Integration findings surfaced by these runs

1. **`search_accounts {count:true}` fails** with HTTP 400. The accounts handler also only reads
   `QueryResponse.Account`, so even a successful count response would come back empty. Accounts must be
   counted from the list. Customers and vendors return `Count: N`.
2. **Tool errors aren't flagged** with `isError`. They arrive as plain text (`Error searching accounts: …`).
3. **Output size:** the 12-month **monthly** P&L is about 21k tokens as raw JSON-RPC, close to Claude
   Code's default 25k MCP output cap (`MAX_MCP_OUTPUT_TOKENS`). In Run 1 Claude chose to re-query month by
   month (12 extra calls, 25 turns, $0.81 total). A larger company would exceed the cap, so Task 2's skill
   should request smaller reports (one quarter, or `summarize_column_by: Total` per month).
4. **Sandbox data oddities** that Claude correctly flagged: the company `StartDate` is 2026-10-11 while
   transactions go back to May 2026, and one account has a last-updated time of 2026-11-15, in the future.
   Confirmed present in the raw tool output.
