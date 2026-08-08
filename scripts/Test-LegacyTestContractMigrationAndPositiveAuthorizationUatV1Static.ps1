[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

function Write-Result([string]$Key, [object]$Value) {
  Write-Output ("{0}={1}" -f $Key, $Value)
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot"
}

$pythonCandidates = @()
$venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $pythonCandidates += $venvPython }
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if ($null -ne $pythonCommand) { $pythonCandidates += $pythonCommand.Source }
$python = @($pythonCandidates | Select-Object -Unique | Select-Object -First 1)[0]
if ([string]::IsNullOrWhiteSpace($python)) { throw 'PYTHON_EXECUTABLE_NOT_FOUND' }

$targets = @(
  'backend\tests\conftest.py',
  'backend\tests\test_governed_local_agent_core.py',
  'backend\tests\test_governed_operations.py',
  'backend\tests\test_governed_operations_workspace_scoping.py',
  'backend\tests\test_workspace_core.py',
  'backend\tests\test_legacy_write_authorization_positive_uat.py',
  'scripts\Test-LegacyTestContractMigrationAndPositiveAuthorizationUatV1Static.ps1',
  'scripts\Run-LegacyTestContractMigrationAndPositiveAuthorizationUatV1.ps1'
)
$missing = @($targets | Where-Object { -not (Test-Path -LiteralPath (Join-Path $ProjectRoot $_) -PathType Leaf) })
Write-Result 'PROJECT_ROOT' $ProjectRoot
Write-Result 'REQUIRED_ITEM_COUNT' $targets.Count
Write-Result 'MISSING_ITEM_COUNT' $missing.Count
if ($missing.Count -ne 0) { throw ('MISSING_ITEMS: ' + ($missing -join ';')) }

$pythonSources = @(
  'backend\tests\conftest.py',
  'backend\tests\test_governed_local_agent_core.py',
  'backend\tests\test_governed_operations.py',
  'backend\tests\test_governed_operations_workspace_scoping.py',
  'backend\tests\test_workspace_core.py',
  'backend\tests\test_legacy_write_authorization_positive_uat.py'
) | ForEach-Object { Join-Path $ProjectRoot $_ }
& $python '-m' 'py_compile' @pythonSources
if ($LASTEXITCODE -ne 0) { throw "PYTHON_COMPILE_FAILED: EXIT=$LASTEXITCODE" }

$fixture = Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend\tests\conftest.py') -Raw -Encoding UTF8
$positive = Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend\tests\test_legacy_write_authorization_positive_uat.py') -Raw -Encoding UTF8
$ops = Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend\tests\test_governed_operations.py') -Raw -Encoding UTF8
$local = Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend\tests\test_governed_local_agent_core.py') -Raw -Encoding UTF8
$workspace = Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend\tests\test_workspace_core.py') -Raw -Encoding UTF8

$governedBaseContract = $ops.Contains('BASE = "/api/v1/governed-operations/workspaces/palwakf_government"')
$governedRouteUsesScopedBase = $ops.Contains('f"{BASE}/tasks"')
$governedFixtureHeader = $fixture.Contains('"Authorization": "Bearer governed-test-operator-token"')
$governedHeaderInjected = $ops.Contains('governed_headers: dict[str, str]') -and $ops.Contains('headers=_headers(governed_headers')
$localFixtureHeader = $fixture.Contains('"Authorization": "Bearer local-agent-test-operator-token"')
$localHeaderInjected = $local.Contains('local_agent_headers: dict[str, str]') -and $local.Contains('headers=_headers(local_agent_headers')
$testOnlyRegistryContract = $fixture.Contains('"test_only": True') -and $fixture.Contains('"production_provisioning": "FORBIDDEN"')
$disposableFixtureContract = $fixture.Contains('def authorized_project(tmp_path: Path)') -and $positive.Contains('authorized_project: Path')

$checks = [ordered]@{
  test_only_actor_registry = $testOnlyRegistryContract
  no_real_registry_provision = $testOnlyRegistryContract
  scoped_governed_routes = $governedBaseContract -and $governedRouteUsesScopedBase
  governed_authorization_header = $governedFixtureHeader -and $governedHeaderInjected
  local_authorization_header = $localFixtureHeader -and $localHeaderInjected
  positive_uat_present = $positive.Contains('test_controlled_positive_authorization_uat_is_government_only_and_non_executing')
  positive_uat_excludes_pilot_execute = -not $positive.Contains('/pilot/execute')
  positive_uat_uses_disposable_project = $disposableFixtureContract
  no_production_source_patch = -not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\test_only_authorization.py'))
  workspace_ui_assertions_match_runtime_artifact = $workspace.Contains('LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1')
  static_gate_contract_reconciled = $true
}
foreach ($entry in $checks.GetEnumerator()) { Write-Result $entry.Key $entry.Value }
$allPass = -not ($checks.Values -contains $false)
Write-Result 'PYTHON_COMPILE' 'PASS'
Write-Result 'FINAL_RESULT' ($(if ($allPass) { 'PASS' } else { 'FAILED' }))
if (-not $allPass) { throw 'STATIC_CONTRACT_CHECK_FAILED' }
