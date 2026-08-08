[CmdletBinding()]
param(
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$script = Join-Path $PSScriptRoot "scripts\run_governed_live_probe_v1.py"
& $Python $script --self-test
if ($LASTEXITCODE -ne 0) { throw "HARNESS_SELF_TEST_FAILED=$LASTEXITCODE" }
Write-Host "HARNESS_SELF_TEST_WRAPPER=PASS"
