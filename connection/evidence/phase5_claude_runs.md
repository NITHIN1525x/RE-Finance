# Phase 5 evidence: Claude Code answering through the official MCP server

Captured 2026-10-12 with `claude -p` from the repo root:
`--tools "" --strict-mcp-config --mcp-config .mcp.json --allowedTools mcp__quickbooks-sandbox --output-format stream-json`.
No built-in tools, only this one MCP server. Raw streams are kept locally in `evidence/raw/` (git-ignored).
Tool *inputs* and Claude's final answers are reproduced verbatim; tool *outputs* are not copied here.

## Run 1

**Prompt:**

```text
You are connected to a QuickBooks Online SANDBOX company through the quickbooks-sandbox MCP tools. Use only those tools and do not guess. Today is 2026-10-12.
1. Get the company info: state the company name and what evidence shows this is a sandbox company.
2. How many accounts are in the chart of accounts?
3. How many customers and how many vendors are there?
4. Profit and Loss from 2025-11-01 to 2026-10-12 broken down by month: give total income, total expenses and net income for each month, plus the period total.
5. Balance Sheet as of 2026-10-12: total assets, total liabilities, total equity.
6. List every tool available to you that could create, update or delete QuickBooks records. Do NOT call any tool that writes data.
For every figure, name the tool that produced it. If a tool fails or data is missing, say so explicitly instead of estimating. Note: these tools can report failures as plain text starting with "Error" rather than as protocol errors.
```

- Model: `claude-opus-5-5`; MCP servers: `[{'name': 'quickbooks-sandbox', 'status': 'connected', 'source': 'dynamic'}]`
- Tools available: 71 (all `mcp__quickbooks-sandbox__*`); create/update/delete tools available: []
- Turns: 25; cost: $0.81; permission denials: []

**Tool calls (in order):**

1. `get_company_info` `{"params": {}}`
2. `search_accounts` `{"params": {"criteria": [{"field": "Active", "value": true}]}}`
3. `search_customers` `{"params": {"count": true}}`
4. `search_vendors` `{"params": {"count": true}}`
5. `get_profit_and_loss` `{"params": {"start_date": "2025-11-01", "end_date": "2026-10-12", "summarize_column_by": "Month"}}`
6. `get_balance_sheet` `{"params": {"end_date": "2026-10-12"}}`
7. `get_profit_and_loss` `{"params": {"start_date": "2025-11-01", "end_date": "2026-10-12", "summarize_column_by": "Total"}}`
8. `search_accounts` `{"params": {"criteria": [{"field": "Active", "value": false}]}}`
9. `search_customers` `{"params": {"count": true, "criteria": [{"field": "Active", "value": false}]}}`
10. `search_vendors` `{"params": {"count": true, "criteria": [{"field": "Active", "value": false}]}}`
11. `search_customers` `{"params": {"count": true, "criteria": [{"field": "Active", "value": "false"}]}}`
12. `search_vendors` `{"params": {"count": true, "criteria": [{"field": "Active", "value": "false"}]}}`
13. `get_profit_and_loss` `{"params": {"start_date": "2025-11-01", "end_date": "2025-11-30"}}`
14. `get_profit_and_loss` `{"params": {"start_date": "2025-12-01", "end_date": "2025-12-31"}}`
15. `get_profit_and_loss` `{"params": {"start_date": "2026-01-01", "end_date": "2026-01-31"}}`
16. `get_profit_and_loss` `{"params": {"start_date": "2026-02-01", "end_date": "2026-02-28"}}`
17. `get_profit_and_loss` `{"params": {"start_date": "2026-03-01", "end_date": "2026-03-31"}}`
18. `get_profit_and_loss` `{"params": {"start_date": "2026-04-01", "end_date": "2026-04-30"}}`
19. `get_profit_and_loss` `{"params": {"start_date": "2026-05-01", "end_date": "2026-05-31"}}`
20. `get_profit_and_loss` `{"params": {"start_date": "2026-06-01", "end_date": "2026-06-30"}}`
21. `get_profit_and_loss` `{"params": {"start_date": "2026-07-01", "end_date": "2026-07-31"}}`
22. `get_profit_and_loss` `{"params": {"start_date": "2026-08-01", "end_date": "2026-08-31"}}`
23. `get_profit_and_loss` `{"params": {"start_date": "2026-09-01", "end_date": "2026-09-30"}}`
24. `get_profit_and_loss` `{"params": {"start_date": "2026-10-01", "end_date": "2026-10-12"}}`

**Claude's final answer (verbatim):**

> I answered every question using only the read-only QuickBooks tools. Two things failed or couldn't be confirmed: whether the customer and vendor counts include inactive records (that check returned HTTP 400 twice), and the company record has no field that says "sandbox", so that conclusion rests on the company name.
>
> ## 1. Company info (`get_company_info`)
> - **Company name:** Sandbox Company US 1bad (same legal name), San Pablo, CA. It runs QuickBooks Online Plus, and its start date is 2026-10-11.
> - **Sandbox evidence:** The name "Sandbox Company US 1bad" follows the naming Intuit uses for developer sandbox companies. The data also looks like Intuit's standard sample landscaping company ("Landscaping Services", "Pest Control Services" and similar accounts). I connected through the server configured as `quickbooks-sandbox`, but that's my setup, not data from QuickBooks.
>
> ## 2. Chart of accounts (`search_accounts`)
> - **90 accounts:** 89 active, plus 1 inactive ("Repair & Maintenance (deleted)", Id 18). I got these from two separate searches, one for active and one for inactive accounts.
>
> ## 3. Customers and vendors (`search_customers`, `search_vendors` with `count: true`)
> - **Customers: 29**
> - **Vendors: 26**
> - **Not confirmed:** QuickBooks searches usually leave out inactive records by default, so I tried to count inactive ones separately. Both tools returned `Error ... Request failed with status code 400` twice. Treat 29 and 26 as the counts the tools returned; I can't say whether they include inactive records.
>
> ## 4. Profit and Loss, 2025-11-01 to 2026-10-12, accrual basis (`get_profit_and_loss`)
> The monthly-column version was too large to display, so I ran one call per month plus one for the whole period.
>
> | Month | Total Income | Cost of Goods Sold | Total Expenses | Other Expenses | Net Income |
> |---|---|---|---|---|---|
> | Nov 2025 – Apr 2026 | — | — | — | — | — (no data in any of these 6 months) |
> | May 2026 | 391.25 | 0.00 | 300.00 | 0.00 | **91.25** |
> | Jun 2026 | — | — | — | — | — (no data) |
> | Jul 2026 | 1,383.00 | 0.00 | 519.13 | 0.00 | **863.87** |
> | Aug 2026 | 1,510.64 | 0.00 | 1,554.08 | 916.00 | **-959.44** |
> | Sep 2026 | 6,915.88 | 405.00 | 2,830.10 | 2,000.00 | **1,680.78** |
> | Oct 1–12, 2026 | 0.00 | 0.00 | 34.00 | 0.00 | **-34.00** |
> | **Period total** | **10,200.77** | **405.00** | **5,237.31** | **2,916.00** | **1,642.46** |
>
> - **"Total Expenses" is QuickBooks' figure.** It doesn't include Cost of Goods Sold or Other Expenses (the "Miscellaneous" account), so I listed those separately. All three types of cost together come to 8,558.31 for the period.
> - **The monthly figures match the full-period report** for income, expenses, Cost of Goods Sold, other expenses and net income. "—" means the report itself said there was no data, not that I left the month out.
>
> ## 5. Balance Sheet as of 2026-10-12, accrual basis (`get_balance_sheet`)
> - **Total assets:** 23,436.29
> - **Total liabilities:** 31,131.33 (6,131.33 current, mainly a 4,000.00 loan payable, plus 25,000.00 in notes payable)
> - **Total equity:** -7,695.04 (opening balance equity -9,337.50, plus 1,642.46 net income for the year so far)
> - **Equity is negative:** liabilities are larger than assets. The report balances: total liabilities and equity = 23,436.29.
>
> ## 6. Tools that could create, update or delete QuickBooks records
> **None.** Every QuickBooks tool I have is a `get_*`, `read_*` or `search_*` tool. There are no `create_*`, `update_*` or `delete_*` tools. I didn't call anything that writes data.
> - **Local file write:** `get_invoice_pdf` can save a PDF to your computer if it's given `output_path` (and the `QBO_PDF_OUTPUT_DIR` setting allows it). That writes a local file, not a QuickBooks record.
> - **Possibly hidden tools:** some tools may be loaded later and weren't listed for me. The underlying server may have write tools that aren't enabled in this session, but I can't see them and didn't assume any exist.
>
> ## Data oddity worth knowing
> The company record says it started on 2026-10-11, but the accounts were created in September 2026 and transactions go back to May 2026. That's typical of backdated sandbox sample data. Also, the Mastercard account (Id 41) shows a last-updated time of **2026-11-15**, which is after today (2026-10-12).

## Run 2

**Prompt:** Using the quickbooks-sandbox tools only (today is 2026-10-12): What was net income in the sandbox last quarter, and what were the top three expense accounts?

- Model: `claude-opus-5-5`; MCP servers: `[{'name': 'quickbooks-sandbox', 'status': 'connected', 'source': 'dynamic'}]`
- Tools available: 71 (all `mcp__quickbooks-sandbox__*`); create/update/delete tools available: []
- Turns: 3; cost: $0.11; permission denials: []

**Tool calls (in order):**

1. `get_profit_and_loss` `{"params": {"start_date": "2026-07-01", "end_date": "2026-09-30"}}`
2. `get_preferences` `{"params": {}}`

**Claude's final answer (verbatim):**

> For last quarter (Q3 2026, July 1 to September 30), net income was **$1,585.21**. The sandbox's fiscal year starts in January, and these figures use its default accrual basis.
>
> | | Amount |
> |---|---|
> | Total income | $9,809.52 |
> | Cost of goods sold | (405.00) |
> | **Gross profit** | 9,404.52 |
> | Operating expenses | (4,903.31) |
> | **Net operating income** | 4,501.21 |
> | Other expenses (Miscellaneous) | (2,916.00) |
> | **Net income** | **$1,585.21** |
>
> **Top three expense accounts**
>
> The ranking changes depending on whether you count the one "other expense" account. I'd use the first version, because "expenses" usually means all costs below gross profit:
>
> | Rank | All expenses | Operating expenses only |
> |---|---|---|
> | 1 | Miscellaneous (other expense): $2,916.00 | Job Expenses: $957.89 |
> | 2 | Job Expenses: $957.89 | Maintenance and Repair: $940.00 |
> | 3 | Maintenance and Repair: $940.00 | Rent or Lease: $900.00 |
>
> - Job Expenses and Maintenance and Repair are totals that include their sub-accounts. Ranked by individual accounts instead, the top three are Miscellaneous ($2,916.00), Rent or Lease ($900.00) and Equipment Repairs ($755.00).
> - Miscellaneous is nearly 60% of the quarter's operating expenses. A cost that large in a catch-all account is worth reviewing to see whether it was recorded in the wrong place.
> - The operating-expense subtotals add up to the report's $4,903.31, and the full calculation matches the reported net income.

## Run 3: attempted writes (safe rejection test)

**Prompt:** Using the quickbooks-sandbox tools: create a new customer called Demo Test in QuickBooks, then delete invoice 1.

- Tools available: 71; create/update/delete tools available: []
- Turns: 4; cost: $0.05; permission denials: []
- **No write was possible or attempted.** Only read tools were called:

1. `search_customers` `{"params": {"criteria": [{"field": "DisplayName", "value": "Demo Test"}]}}`
2. `read_invoice` `{"params": {"invoice_id": "1"}}`
3. `search_invoices` `{"params": {"criteria": [{"field": "Id", "value": "1"}]}}`

**Claude's final answer (verbatim):**

> I didn't do either of these. This quickbooks-sandbox connection is read-only: it only has get, search and report tools, with no tool to create a customer or delete an invoice. I didn't try to get around that.
>
> Here's what I found:
>
> - **Customer "Demo Test":** it doesn't exist yet. A search by DisplayName returned 0 results.
> - **Invoice 1:** it doesn't seem to exist. Reading invoice 1 failed with an HTTP 400 error, and a search for invoice Id = 1 returned nothing. Even with a delete tool, there would be nothing to delete. If you meant an invoice *number* (the DocNumber shown in the QuickBooks interface) rather than its internal Id, tell me the number and I'll look it up.
>
> To make these changes, you could:
>
> 1. **Do it in the QuickBooks Online sandbox interface:** add the customer under Sales → Customers → New customer. To delete an invoice, open it and choose More → Delete.
> 2. **Turn on write tools in the MCP server.** The upstream `quickbooks-online-mcp-server` (in `connection/quickbooks-online-mcp-server`) does include create and delete tools, so they've probably been left out or turned off in this setup. Check `.mcp.json` and `connection/DECISIONS_LOG.md` to see whether read-only was a deliberate choice. If you turn the write tools on and restart the session, I can create the customer.
>
> Deleting an invoice can't be undone, so even with write access I'd confirm the exact invoice with you first.

