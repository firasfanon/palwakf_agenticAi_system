[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = "Stop"

foreach ($path in @($PackageRoot, $ProjectRoot)) {
  if (-not (Test-Path -LiteralPath $path -PathType Container)) {
    throw "REQUIRED_DIRECTORY_NOT_FOUND=$path"
  }
}

$configPath = Join-Path $PackageRoot "candidate\config\workspace_capability_matrix_v1.json"
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
  throw "CANDIDATE_MATRIX_NOT_FOUND=$configPath"
}

$matrix = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

$requiredProjectFiles = @(
  "backend\src\palwakf_local_agents\app.py",
  "backend\src\palwakf_local_agents\local_agent_core\__init__.py",
  "backend\src\palwakf_local_agents\local_agent_core\contracts.py",
  "backend\src\palwakf_local_agents\local_agent_core\policy.py",
  "backend\src\palwakf_local_agents\local_agent_core\router.py",
  "backend\src\palwakf_local_agents\local_agent_core\store.py",
  "backend\tests\test_governed_local_agent_core.py",
  "config\local_agent_model_pilot_v1.json"
)

$rows = @()
$failures = @()

foreach ($relative in $requiredProjectFiles) {
  $path = Join-Path $ProjectRoot $relative
  $exists = Test-Path -LiteralPath $path -PathType Leaf
  $hash = $null

  if ($exists) {
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  }
  else {
    $failures += "REQUIRED_PROJECT_FILE_MISSING=$relative"
  }

  $rows += [pscustomobject]@{
    RelativePath = $relative
    Exists = $exists
    SHA256 = $hash
  }
}

$appPath = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
$appImportCount = 0
$appMountCount = 0

if (Test-Path -LiteralPath $appPath -PathType Leaf) {
  $appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
  $appImportCount = [regex]::Matches($appText, "from \.local_agent_core import mount_local_agent_core").Count
  $appMountCount = [regex]::Matches($appText, "mount_local_agent_core\(app, project_root=PROJECT_ROOT\)").Count

  if ($appImportCount -ne 1) { $failures += "LOCAL_AGENT_CORE_IMPORT_COUNT_INVALID=$appImportCount" }
  if ($appMountCount -ne 1) { $failures += "LOCAL_AGENT_CORE_MOUNT_COUNT_INVALID=$appMountCount" }
}

$pilotConfigPath = Join-Path $ProjectRoot "config\local_agent_model_pilot_v1.json"
$pilotConfigContract = "NOT_PRESENT"

if (Test-Path -LiteralPath $pilotConfigPath -PathType Leaf) {
  try {
    $pilot = Get-Content -LiteralPath $pilotConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $pilotConfigContract = if (
      $pilot.enabled -eq $false -and
      $pilot.provider -eq "ollama_local_only" -and
      $pilot.external_network -eq "NONE"
    ) { "DISABLED_LOCAL_ONLY_CONTRACT_MATCH" } else { "PRESENT_BUT_CONTRACT_MISMATCH" }

    if ($pilotConfigContract -ne "DISABLED_LOCAL_ONLY_CONTRACT_MATCH") {
      $failures += "PILOT_CONFIG_CONTRACT_INVALID=$pilotConfigContract"
    }
  }
  catch {
    $pilotConfigContract = "PRESENT_BUT_INVALID_JSON"
    $failures += "PILOT_CONFIG_INVALID_JSON"
  }
}

$workspaceRows = @()

foreach ($workspace in $matrix.workspaces) {
  $workspaceId = [string]$workspace.workspace_id
  $workspacePath = Join-Path $ProjectRoot ("workspaces\" + $workspaceId)
  $exists = Test-Path -LiteralPath $workspacePath -PathType Container

  if (-not $exists) {
    $failures += "WORKSPACE_DIRECTORY_MISSING=$workspaceId"
  }

  $workspaceRows += [pscustomobject]@{
    WorkspaceId = $workspaceId
    ProfileId = [string]$workspace.profile_id
    Exists = $exists
    FutureModelPilot = [string]$workspace.future_model_pilot
  }
}

$manifestDirectory = Join-Path $env:TEMP ("multi_workspace_agent_capability_expansion_v1_baseline_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
$manifestPath = Join-Path $manifestDirectory "baseline_manifest.json"

$manifest = [ordered]@{
  contract = "MEGA_BATCH_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1"
  captured_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot
  app_import_count = $appImportCount
  app_mount_count = $appMountCount
  pilot_config_contract = $pilotConfigContract
  project_files = $rows
  workspaces = $workspaceRows
  failure_count = $failures.Count
  failures = $failures
  global_defaults = $matrix.global_defaults
}

$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

"===== MULTI-WORKSPACE AGENT CAPABILITY EXPANSION V1 BASELINE ====="
$rows | Format-Table RelativePath, Exists, SHA256 -AutoSize
$workspaceRows | Format-Table WorkspaceId, ProfileId, Exists, FutureModelPilot -AutoSize
"LOCAL_AGENT_CORE_IMPORT_COUNT=$appImportCount"
"LOCAL_AGENT_CORE_MOUNT_COUNT=$appMountCount"
"PILOT_CONFIG_SECURITY_CONTRACT=$pilotConfigContract"
"BASELINE_MANIFEST=$manifestPath"
"BASELINE_FAILURE_COUNT=$($failures.Count)"
"PROJECT_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"SHELL_EXECUTION=NONE"
"GIT_WRITE=NONE"
"PROJECT_FILE_WRITE=NONE"
"EXTERNAL_NETWORK=NONE"

if ($failures.Count -gt 0) {
  throw "MULTI_WORKSPACE_BASELINE_NOT_CLEAN=$($failures -join ';')"
}

"BASELINE_RESULT=PASS"
