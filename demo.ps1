# Seed a fictional NAS and convene the board for the three Round 1 scenarios.
# The library only appends. This script stages a fresh ledger so the showcase
# is exactly these three receipts.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (Get-Command python -ErrorAction SilentlyContinue) {
    $Py = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Py = "py"
} else {
    Write-Error "Python 3.10 or newer is required."
    exit 1
}

& $Py -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3.10 or newer is required."
    exit 1
}

$Nas = if ($env:BOARDROOM_NAS) { $env:BOARDROOM_NAS } else { "demo-nas" }
$Ledger = if ($env:BOARDROOM_LEDGER) { $env:BOARDROOM_LEDGER } else { "ledger/DECISIONS.md" }
$Today = if ($env:BOARDROOM_TODAY) { $env:BOARDROOM_TODAY } else { "2026-10-26" }
$env:PYTHONUNBUFFERED = "1"

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Older hosts keep their current encoding. The transcript is ASCII.
}

Write-Host "THE NAS BOARDROOM"
Write-Host "Seeding a fictional volume at $Nas"
Write-Host "Calendar pinned to $Today so last quarter stays Q3 2026."
Write-Host "Speeches use a local Ollama model only when one is already listening on 127.0.0.1."
Write-Host ""

& $Py -m boardroom.seed --nas "$Nas" --reset-ledger "$Ledger"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

function Invoke-Scenario {
    param(
        [string]$Title,
        [string]$Request
    )
    Write-Host ""
    Write-Host ("=" * 72)
    Write-Host "SCENARIO  $Title"
    Write-Host ("=" * 72)
    Write-Host ""
    & $Py -m boardroom --nas "$Nas" --ledger "$Ledger" --today "$Today" "$Request"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Invoke-Scenario "a. Duplicate-cleanup proposal" "find duplicate photos and propose cleanup"
Invoke-Scenario "b. What did I sign last quarter?" "what did I sign last quarter?"
Invoke-Scenario "c. Risky delete the Auditor blocks" "delete all files in Documents/Contracts, including the signed originals"

Write-Host ""
Write-Host "Three sessions are on the record in ${Ledger}:"
Select-String -Path $Ledger -Pattern "^## BRD-" | ForEach-Object { $_.Line }
