<#
.SYNOPSIS
    One-command demo: token owner, live sandbox smoke test, deterministic skill run, key figures, submission rebuild.

.DESCRIPTION
    Free: no Claude calls. The smoke test calls the QuickBooks SANDBOX through the official MCP server (read-only).
    Never prints secrets or tokens, and never hands tokens over between Django and the MCP server: if a hand-over is
    needed it prints the command and stops. Stops with a clear message at the first failing step.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\demo.ps1
    powershell -ExecutionPolicy Bypass -File .\demo.ps1 -Client abc-inc-sandbox -OutDir demo-output\demo-run
#>
[CmdletBinding()]
param(
    [string]$Client = 'abc-inc-sandbox',
    # A subfolder, so the demo never overwrites other files in demo-output\ (or the committed trend-reports\).
    [string]$OutDir = 'demo-output\demo-run'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3

$Repo = $PSScriptRoot
$BackendPy = Join-Path $Repo 'connection\backend\.venv\Scripts\python.exe'
$SkillPy = Join-Path $Repo '.claude\skills\monthly-trend-analysis\.venv\Scripts\python.exe'
$ManagePy = Join-Path $Repo 'connection\backend\manage.py'
$script:StepNo = 0

function Write-Step([string]$Title) {
    $script:StepNo++
    Write-Host ''
    Write-Host ("[{0}] {1}" -f $script:StepNo, $Title) -ForegroundColor Cyan
}

function Write-Ok([string]$Message) { Write-Host "    OK  $Message" -ForegroundColor Green }

function Stop-Demo([string]$Message, [string]$Hint) {
    Write-Host ''
    Write-Host ("DEMO STOPPED at step {0}: {1}" -f $script:StepNo, $Message) -ForegroundColor Red
    if ($Hint) { Write-Host $Hint -ForegroundColor Yellow }
    exit 1
}

Set-Location $Repo

# ------------------------------------------------------------------------------------------------ 1
Write-Step 'Prerequisites'
foreach ($path in @($BackendPy, $SkillPy)) {
    if (-not (Test-Path $path)) {
        Stop-Demo "missing $path" 'Create the environments first: connection\QUICKSTART.md step 3 (backend) and README "Task 2" (skill).'
    }
}
Write-Ok 'backend and skill Python environments found'

# ------------------------------------------------------------------------------------------------ 2
Write-Step "Who owns the QuickBooks token for '$Client'"
if ($Client -notmatch '^[A-Za-z0-9_-]+$') { Stop-Demo "invalid client slug '$Client'" }
# Reads ONLY the owner field. One line of Python with single quotes only, so PowerShell passes it through intact.
$query = "from qbo.models import QBOConnection as C; c = C.objects.filter(client__slug='$Client').first(); " +
         "print('OWNER=' + (c.token_owner if c else 'none'))"
$ownerOut = & $BackendPy $ManagePy shell -v 0 -c $query
if ($LASTEXITCODE -ne 0) { Stop-Demo 'could not read the connection from Django' 'Check connection\backend (venv, migrations, connection\.secrets\backend.env).' }
$owner = ($ownerOut | Select-String -Pattern '^OWNER=(\w+)$' | Select-Object -First 1)
if (-not $owner) { Stop-Demo 'Django did not report a token owner' }
$owner = $owner.Matches[0].Groups[1].Value
switch ($owner) {
    'mcp' { Write-Ok 'the MCP server owns the token (checked out), so the live smoke test can run' }
    'django' {
        Stop-Demo 'Django owns the token, so the MCP server has none and the live smoke test cannot run.' (
            "This script never hands tokens over. To hand it to the MCP server yourself, run:`n" +
            "    connection\backend\.venv\Scripts\python connection\backend\manage.py export_mcp_env --client $Client`n" +
            "then run .\demo.ps1 again.")
    }
    'none' { Stop-Demo "client '$Client' has no QuickBooks connection" 'Connect it in the Connection Console first (connection\QUICKSTART.md step 5).' }
    default { Stop-Demo "unexpected token owner '$owner'" }
}

# ------------------------------------------------------------------------------------------------ 3
Write-Step 'Live smoke test against the QuickBooks sandbox (read-only, no Claude call)'
& $BackendPy (Join-Path $Repo 'connection\scripts\smoke_test') --client $Client
if ($LASTEXITCODE -ne 0) { Stop-Demo "smoke test failed (exit $LASTEXITCODE); see the [FAIL] lines above" 'Troubleshooting: connection\TROUBLESHOOTING.md' }
Write-Ok 'smoke test passed (a Django SKIP while checked out is expected, D-16)'

# ------------------------------------------------------------------------------------------------ 4
Write-Step "Deterministic skill run on the ABC workbook -> $OutDir"
& $SkillPy (Join-Path $Repo '.claude\skills\monthly-trend-analysis\scripts\run_trends.py') --out-dir $OutDir
if ($LASTEXITCODE -ne 0) { Stop-Demo "the skill's engine failed (exit $LASTEXITCODE)" }
$json = Get-ChildItem -Path $OutDir -Filter 'abc-inc-*-trends.json' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $json) { Stop-Demo "no abc-inc-*-trends.json was written to $OutDir" }
Write-Ok "wrote $($json.Name) and its .md (numbers only; Claude writes the commentary in a skill run)"

# ------------------------------------------------------------------------------------------------ 5
$report = Get-Content -Raw -Encoding UTF8 $json.FullName | ConvertFrom-Json
$month = $report.meta.latest_month
Write-Step "Key figures for $month (from the engine's JSON, not typed in)"
$revenue = $report.revenue.total
$margin = @($report.gross_margin.monthly)[-1]
$inv = [System.Globalization.CultureInfo]::InvariantCulture     # 1,234,567.89 whatever the machine's region
Write-Host ('    Total revenue   ' + [string]::Format($inv, '{0,14:N2}   ({1:+0.0;-0.0}% vs {2})', $revenue.latest, $revenue.mom_pct, $report.meta.prior_month))
Write-Host ('    Gross margin    ' + [string]::Format($inv, '{0,13:N1}%   (gross profit {1:N2})', $margin.gm_pct, $margin.gross_profit))
Write-Host ('    Net income      ' + [string]::Format($inv, '{0,14:N2}', $report.net_income.latest))

# ------------------------------------------------------------------------------------------------ 6
Write-Step 'Rebuild submission\ from existing outputs (free; Task 1 is live-only and left as is)'
& $SkillPy (Join-Path $Repo 'scripts\build_submission.py')
if ($LASTEXITCODE -ne 0) {
    Stop-Demo 'submission\ was not fully rebuilt; the failing item kept its previous file (see the message above).' (
        'If Task 2 was refused ("no complete report" or "older than the one already in Task 2 response.md"), ' +
        'trend-reports\ probably holds a numbers-only draft (run_trends.py without --out-dir). Restore the committed ' +
        'report with "git restore trend-reports/" and run .\demo.ps1 again.')
}
Write-Ok 'submission\ is up to date'

# ------------------------------------------------------------------------------------------------ 7
Write-Step 'Results page'
Write-Host '    URL:    http://localhost:5173/#results'
Write-Host '    Start:  cd connection\frontend; npm run dev        (the Results page needs only Vite)'
Write-Host '    Console tab also needs Django:  cd connection\backend; .venv\Scripts\python manage.py runserver localhost:8000'
Write-Host ''
Write-Host "Token still checked out to the MCP server. To hand it back to Django after the demo (close Claude Code first):"
Write-Host "    connection\backend\.venv\Scripts\python connection\backend\manage.py sync_mcp_tokens --client $Client"
Write-Host ''
Write-Host 'Demo complete.' -ForegroundColor Green
exit 0
