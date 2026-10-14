# Task 2 stretch goal: ABC's P&L, loaded into QuickBooks and analysed live

**Result:** ABC Inc's 18-month P&L (Jan 2025 to Jun 2026) was loaded into a brand-new QuickBooks sandbox company,
read back through the Task 1 read-only MCP server, and analysed by the **unchanged** skill. Every month matches the
workbook run to the cent: **21 metrics × 18 months, 0 differences.** Done on 2026-10-14; decision record
[D-62](../connection/DECISIONS_LOG.md). Everything is in [`stretch/`](../stretch/), and nothing in Tasks 1–4 was changed.

## What ran, in order

| Step | Script | What it did |
|---|---|---|
| 1. Load (write) | `stretch/load_abc_into_sandbox.py --apply --expect-company "Sandbox Company US 8831"` | Built the plan from the skill's own JSON for the workbook. Checked the company name read back from QuickBooks before writing. Created class **ABC-IMPORT** and the accounts, and posted **18 journal entries** (one per month, 1,060 lines), every line tagged with that class. Then read QuickBooks' class-filtered P&L and checked it against the plan. |
| 2. Read | `stretch/read_live_pnl.py` | With its own read-only grant, started the **unchanged** MCP launcher against a temporary token store, then called `search_classes`, `search_accounts` and `get_profit_and_loss` (class filter, by month, three 6-month chunks). |
| 3. Adapt | `stretch/pnl_to_workbook.py` | Laid QuickBooks' report out as a "Profit and Loss" workbook: section headers, account rows, and QuickBooks' own Total, Gross Profit and Net Income rows. It computes no numbers. |
| 4. Analyse | the skill, via `claude -p` | One real skill run (claude-opus-5-5, $0.3848, 46 s): `run_trends.py` on the live workbook, then Claude's commentary. Output is in `demo-output/stretch/live-run/` (git-ignored). |
| 5. Compare | `stretch/compare_live_vs_workbook.py` | Compared the live run with the workbook run, month by month. |

`stretch/test_stretch.py` has 13 offline tests (no network): the plan balances, the account rename and reuse rules, the
clearing account, the adapter, and the comparison.

## Month by month: live (QuickBooks via MCP) vs workbook

| Month | Revenue (workbook) | Revenue (live) | GM % (workbook) | GM % (live) | Opex (workbook) | Opex (live) | Net income (workbook) | Net income (live) | Max difference |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan 2025 | 167,587.50 | 167,587.50 | 77.9515 | 77.9515 | 513,541.99 | 513,541.99 | -382,905.03 | -382,905.03 | 0.00 |
| Feb 2025 | 176,651.19 | 176,651.19 | 78.7851 | 78.7851 | 555,578.55 | 555,578.55 | -416,403.65 | -416,403.65 | 0.00 |
| Mar 2025 | 170,550.65 | 170,550.65 | 70.6836 | 70.6836 | 533,111.68 | 533,111.68 | -412,560.37 | -412,560.37 | 0.00 |
| Apr 2025 | 154,136.03 | 154,136.03 | 67.8526 | 67.8526 | 495,053.56 | 495,053.56 | -390,468.24 | -390,468.24 | 0.00 |
| May 2025 | 169,403.74 | 169,403.74 | 70.3596 | 70.3596 | 473,844.16 | 473,844.16 | -354,652.31 | -354,652.31 | 0.00 |
| Jun 2025 | 190,555.65 | 190,555.65 | 74.3225 | 74.3225 | 497,871.96 | 497,871.96 | -356,246.22 | -356,246.22 | 0.00 |
| Jul 2025 | 183,919.10 | 183,919.10 | 70.3233 | 70.3233 | 455,324.92 | 455,324.92 | -325,986.96 | -325,986.96 | 0.00 |
| Aug 2025 | 181,747.20 | 181,747.20 | 63.0187 | 63.0187 | 431,306.59 | 431,306.59 | -316,771.89 | -316,771.89 | 0.00 |
| Sep 2025 | 181,508.47 | 181,508.47 | 68.0373 | 68.0373 | 483,844.86 | 483,844.86 | -360,351.45 | -360,351.45 | 0.00 |
| Oct 2025 | 191,426.63 | 191,426.63 | 69.3161 | 69.3161 | 479,083.78 | 479,083.78 | -346,394.22 | -346,394.22 | 0.00 |
| Nov 2025 | 187,800.63 | 187,800.63 | 71.0077 | 71.0077 | 420,263.04 | 420,263.04 | -286,910.04 | -286,910.04 | 0.00 |
| Dec 2025 | 190,029.49 | 190,029.49 | 69.6783 | 69.6783 | -402,142.09 | -402,142.09 | 534,551.41 | 534,551.41 | 0.00 |
| Jan 2026 | 204,153.96 | 204,153.96 | 70.2405 | 70.2405 | 487,711.23 | 487,711.23 | -344,312.38 | -344,312.38 | 0.00 |
| Feb 2026 | 183,160.30 | 183,160.30 | 67.6597 | 67.6597 | 500,504.05 | 500,504.05 | -376,578.43 | -376,578.43 | 0.00 |
| Mar 2026 | 191,468.19 | 191,468.19 | 76.0498 | 76.0498 | 421,605.30 | 421,605.30 | -275,994.10 | -275,994.10 | 0.00 |
| Apr 2026 | 204,512.42 | 204,512.42 | 70.6887 | 70.6887 | 465,742.99 | 465,742.99 | -321,175.85 | -321,175.85 | 0.00 |
| May 2026 | 208,350.96 | 208,350.96 | 67.0414 | 67.0414 | 478,781.03 | 478,781.03 | -339,099.60 | -339,099.60 | 0.00 |
| Jun 2026 | 195,898.16 | 195,898.16 | 70.1516 | 70.1516 | 468,181.80 | 468,181.80 | -330,756.08 | -330,756.08 | 0.00 |

"Opex" is the engine's "Total operating expenses (as exported)". It includes the Tax & Interest (non-operating)
category, which is why December 2025, with its 1,244,430 Income Tax Benefit, is negative.

The comparison also covers COGS, gross profit, all 6 non-zero revenue streams and all 9 expense categories: 21
metrics in total, with tolerances of 0.01 for amounts and 0.0001 points for percentages. **None differs in any month.**
QuickBooks agreed even before the skill ran: the loader's self-check of QuickBooks' class-filtered P&L (Total Income,
Total Cost of Goods Sold, Total Expenses) matched the plan in all 18 months.

## Known cosmetic differences (no effect on any total)

These only change names or layout. Revenue, COGS, every category and net income are identical, as shown above.

1. **Renamed "(ABC)" accounts (1):** **Depreciation → `Depreciation (ABC)`.** The sandbox's sample data already has a
   "Depreciation" account of type *Other Expense*, and ABC's is an operating *Expense*. Posting to the existing account
   would have moved it to another section of the P&L, so the loader created its own account with the suffix. The
   engine still maps it to the same category, Facilities & Office.
2. **Reused same-name accounts (3):** **Insurance**, **Office Expenses** and **Travel**. These come from Intuit's sample
   data (created 2026-09-09) and already had the right type (Expense), so ABC's lines were posted to them. Their own
   sample transactions don't appear in the results because every report is filtered to the ABC-IMPORT class.
3. **Accounts created by the loader (79):** every other account, plus the balance-sheet clearing account. The final
   loader run reported 81 accounts as "already there" because two interrupted runs had created 78 of them (20 in the
   first run, which stopped at the Depreciation clash; 58 in the second, which stopped at the clearing account). The
   third run created the last one. `search_accounts` settles which is which: a creation time after the ABC-IMPORT
   class means the loader created it (`demo-output/stretch/live/accounts-census.json`).
4. **Sub-accounts instead of "Parent: Child" names (8):** QuickBooks doesn't allow ":" in an account name, so each
   `Marketing/Advertising: X` account became sub-account **X** of **Marketing/Advertising**: 3rd Party Content
   Syndication, Ad Spend, Content, Membership Dues/Subscriptions, Miscellaneous, Partner Marketing, Print & Digital
   and Website. "Marketing/Advertising" has amounts of its own as well, so QuickBooks reports them on its header row.
   The adapter writes them as a same-name account row, as the source workbook does. As a result:
   - the live P&L has one extra subtotal, QuickBooks' "Total Marketing/Advertising", which the engine checks: 6
     subtotal rows instead of 5, 0 mismatches;
   - the account group reads "Marketing > Marketing/Advertising" instead of "Marketing";
   - the category stays Sales & Marketing.
5. **Four accounts that are zero in every month were not loaded:** Sales & Marketing - Workers Comp Insurance,
   Sales & Marketing Payroll, Sales & Marketing Payroll Taxes, and Sales and Marketing - Payroll benefits. QuickBooks
   doesn't report accounts with no activity.
6. **Labels:**
   - QuickBooks calls operating income "Net Operating Income" (the workbook says "Operating Income"); both checks pass.
   - The company title is "ABC Inc (live QBO sandbox)", so the output files are named `abc-inc-live-qbo-sandbox-2026-06-trends.*`.
7. **No balance sheet:** the stretch covers the P&L only. The live run therefore has:
   - 29 flags instead of 30, missing only the high-severity cash flag ("Cash and Cash Equivalents" Jun 2026);
   - 4 data-quality checks instead of 6, missing only the two balance-sheet checks.

   Claude's commentary says so: *"the export is a P&L only, so there is no balance sheet and no cash movement can be
   reported."*

## How it stayed safe

- **A new company only.** The loader and the reader both read the company name back from QuickBooks before doing
  anything else and stop unless it is exactly `Sandbox Company US 8831`. They also refuse the demo company's realm,
  compared by SHA-256 hash, so the realm ID is never printed. Both companies' realms start with "9341"; the hashes
  differ. Every API call is refused unless it goes to `sandbox-quickbooks.api.intuit.com`.
- **The demo connection (abc-inc-sandbox) was not touched:** no hand-over, token sync, revoke or disconnect. Its
  QuickBooks company received no writes.
- **Writes used a separate, throwaway grant.** Each write run had its own short-lived sign-in. The grant was revoked
  in a `finally` block and the revocation confirmed: refreshing it then fails with `invalid_grant`. Its token file
  (`connection/.secrets/stretch-write.env`, owner-only) was deleted. This held after each of the three runs,
  including the two that stopped.
- **Reads used the unchanged read-only path.** The reader had its own read-only grant and a temporary token store
  (`connection/.secrets/stretch-read-mcp.env`) with all three `QUICKBOOKS_DISABLE_*` flags set. It reached it through
  the launcher's existing `QBO_MCP_TOKEN_STORE` override. The launcher reported "sandbox, read-only", and `tools/list`
  showed 71 tools with 0 write tools. The grant was revoked and confirmed, and the store deleted. `.mcp.json`, the
  launcher, the MCP server, Django and the demo token store are unchanged.
- **The ~21k-token output limit:** each 6-month chunk of the P&L was about 67–72k characters (an estimated
  16.7–18.0k tokens), so a single MCP call per chunk fits the limit. The full 18 months (~51k tokens) would not.
- **Secrets:** no tokens, client secret or full realm ID were printed or written outside `connection/.secrets/`.
  The sign-in URL went to a `.secrets` file and the browser, never to the terminal. `secret_scan` passes on
  `stretch/` and `demo-output/stretch/`.

## Not covered

- **Balance sheet:** not loaded, so there is no cash flag or balance-sheet check in the live run (difference 7 above).
- **Transaction detail:** each month is a single journal entry per account, not ABC's underlying invoices and bills.
  The P&L totals are exact, but drill-downs in QuickBooks show journal entries.
- **Sample data:** the company also holds Intuit's sample data. The class filter keeps it out of every number above.
  An unfiltered P&L of this company would include it.

## Reproduce

Needs your own Intuit app, a new sandbox company, and the redirect URI `http://localhost:8765/stretch/callback`
added to the app. Remove the redirect URI afterwards. Commands are from the repo root, using the skill's venv as `PY`:

```powershell
$PY = ".claude/skills/monthly-trend-analysis/.venv/Scripts/python"
& $PY .claude/skills/monthly-trend-analysis/scripts/run_trends.py --out-dir demo-output/stretch/workbook-run  # free
& $PY stretch/load_abc_into_sandbox.py                                   # dry run: nothing sent
& $PY stretch/load_abc_into_sandbox.py --apply --expect-company "<new company name>"   # browser sign-in
& $PY stretch/read_live_pnl.py                                           # browser sign-in (read-only)
& $PY stretch/pnl_to_workbook.py
claude -p 'I need the monthly trend analysis for ABC Inc for June 2026 from the workbook at "demo-output/stretch/live/abc-live-pnl.xlsx" (exported from our QuickBooks sandbox, P&L only). Keep it factual. Save the report files in demo-output/stretch/live-run.' --allowedTools "Skill Bash Read Edit Write Glob Grep"
& $PY stretch/compare_live_vs_workbook.py                                # exits 1 on any difference
& $PY stretch/test_stretch.py                                            # 13 offline tests
```

Re-running `--apply` is safe: classes and accounts are reused, and a journal entry whose DocNumber already exists
(`ABC-IMPORT-YYYY-MM`) is skipped. `--revoke-only` revokes a write grant left on file.

**Cost:** one skill run, $0.3848. The load, read, adapter and comparison steps make no Claude calls.
