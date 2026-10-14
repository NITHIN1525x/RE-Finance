# New client in 10 minutes

Point the skill at a new company's export **without changing code**. The worked example is Bluebird Bakery, the
second workbook the skill was proven on (D-34). Commands are PowerShell from the repo root; the skill's venv must
exist (README "Task 2"). **Never commit a real client's workbook or outputs.** Keep the workbook outside the repo, or
in `demo-output\` (git-ignored).

```powershell
$py = ".claude\skills\monthly-trend-analysis\.venv\Scripts\python"
$wb = ".claude\skills\monthly-trend-analysis\tests\test_data\bluebird-bakery.xlsx"   # the client's export
```

**1. Run once with the default rules and read the gaps.**
```powershell
& $py .claude\skills\monthly-trend-analysis\scripts\run_trends.py $wb --out-dir demo-output\bluebird
$r = Get-Content -Raw demo-output\bluebird\bluebird-bakery-co-2026-09-trends.json | ConvertFrom-Json
$r.operating_expenses.fallback_accounts                # accounts no rule matched ("Other Opex")
$r.data_quality.warnings | Select-Object type, detail | Format-List
```
- Bluebird's "Other" holds Instagram Ads, Mystery Shopper Program and Supplier Rebates.
- There are three data-quality warnings: an inferred `Total Delivery` group, a blank `Charitable Donations` account,
  and `Total for Professional Services` stating 2,225.00 against detail rows of 2,200.00 in Mar 2026.

**2. Copy the category config for this client** (it's data, not code: D-33).
```powershell
New-Item -ItemType Directory -Force clients\bluebird | Out-Null
Copy-Item .claude\skills\monthly-trend-analysis\references\category_map.json clients\bluebird\category_map.json
```

**3. Adjust the rules.** Patterns are case-insensitive regexes, and the first matching rule wins. For Bluebird, add
`"instagram", "\\bads?\\b"` to the `patterns` of the `"Sales & Marketing"` rule in
`clients\bluebird\category_map.json`. Leave a genuinely unclassifiable account (Mystery Shopper Program) or a contra
account (Supplier Rebates) in "Other". It is listed by name in the report, so the reviewer sees it.

**4. Re-run with the client's config and check.**
```powershell
& $py .claude\skills\monthly-trend-analysis\scripts\run_trends.py $wb --config clients\bluebird\category_map.json --out-dir demo-output\bluebird
```
- "Other" should now hold only Mystery Shopper Program and Supplier Rebates, with Instagram Ads under Sales &
  Marketing.
- **Data-quality warnings are for the reviewer, not for you to fix.** The engine always uses the detail rows and
  says so. Send the 25.00 mismatch back to the client's bookkeeper.

**5. The full skill run, with Claude's commentary (paid, about $0.40).** In Claude Code at the repo root, ask:
*"Monthly trend analysis for Bluebird Bakery from `<workbook path>`, using the category config
`clients/bluebird/category_map.json`. Save the report in demo-output/bluebird."*

**6. Add one golden case, so a later change can't silently break this client** (`evals/README.md` explains the
grading).
- In `evals/goldens/derive_facts.py`, derive each expected value from **raw cells**, as the `bb.*` facts do. Then
  run `& $py evals\goldens\derive_facts.py` (rewrites `source_facts.json`) and `& $py evals\goldens\derive_facts.py --check`.
- In `evals/goldens/cases.json`, copy a Bluebird case such as `f_bb_from_zero_label`
  ([Task 3.6](../submission/Task%203.6.md)) under a new id (`h_…`). Point its prompt at the client's workbook and
  config, and keep 1–3 structured checks plus the claims that matter.
- Regenerate the readable case files with `& $py scripts\build_submission.py`. Also add the new letter to
  `test_mapping_is_case_order_a_to_g` in `evals/tests/test_submission_docs.py`.
- Run just that case (paid, about $0.45): `& $py evals\run_evals.py --cases h --run-id h-first`. Promote it to the
  baseline only as `evals/REGRESSION.md` §5 describes.
