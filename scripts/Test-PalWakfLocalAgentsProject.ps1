[CmdletBinding()]
param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$required = @(
  'README_AR.md',
  'PROJECT_STATUS_AR.md',
  'MIGRATION_FROM_PLATFORM_AR.md',
  'agents\registry.yaml',
  'governance\OPERATING_BOUNDARIES_V1.md',
  'task_contracts\task_intake_schema.json',
  'backend\src\palwakf_local_agents\app.py',
  'backend\tests\test_api.py',
  'scripts\Import-PlatformReferenceSnapshot.ps1',
  'scripts\Setup-PythonEnvironment.ps1',
  'scripts\Start-LocalAgentBackend.ps1'
)

$missing = @()
foreach ($relative in $required) {
  $path = Join-Path $ProjectRoot $relative
  if (-not (Test-Path -LiteralPath $path)) { $missing += $relative }
}

Write-Host "REQUIRED_FILE_COUNT=$($required.Count)"
Write-Host "MISSING_FILE_COUNT=$($missing.Count)"
Write-Host "PLATFORM_MUTATION=NONE"
Write-Host "DATABASE_ACCESS=NONE"
if ($missing.Count -eq 0) {
  Write-Host "FINAL_RESULT=PASS"
  exit 0
}

$missing | ForEach-Object { Write-Host "MISSING=$($_)" }
Write-Host "FINAL_RESULT=FAIL"
exit 1
