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

$hashPath = Join-Path $PackageRoot "candidate\\accepted_baseline_hashes_v1.json"
$matrixPath = Join-Path $PackageRoot "candidate\\config\\workspace_capability_matrix_v1.json"
if (-not (Test-Path -LiteralPath $hashPath -PathType Leaf)) { throw "ACCEPTED_BASELINE_HASHES_NOT_FOUND" }
if (-not (Test-Path -LiteralPath $matrixPath -PathType Leaf)) { throw "WORKSPACE_MATRIX_NOT_FOUND" }

$hashDocument = Get-Content -LiteralPath $hashPath -Raw -Encoding UTF8 | ConvertFrom-Json
$matrix = Get-Content -LiteralPath $matrixPath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = @()
$sourceRows = @()

foreach ($property in $hashDocument.files.PSObject.Properties) {
  $relativePath = [string]$property.Name
  $path = Join-Path $ProjectRoot $relativePath
  $exists = Test-Path -LiteralPath $path -PathType Leaf
  $actualHash = $null
  $state = "MISSING"

  if ($exists) {
    $actualHash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actualHash -eq [string]$property.Value) {
      $state = "TARGET_EQUALS_ACCEPTED_BASELINE"
    }
    else {
      $state = "TARGET_HASH_MISMATCH"
      $failures += "BASELINE_HASH_MISMATCH=$relativePath"
    }
  }
  else {
    $failures += "BASELINE_FILE_MISSING=$relativePath"
  }

  $sourceRows += [pscustomobject]@{
    RelativePath = $relativePath
    State = $state
    ActualHash = $actualHash
  }
}

# Anchor reconciliation repair:
# PowerShell regex uses a single backslash to escape regex metacharacters.
# The prior candidate used double backslashes and therefore searched for literal backslashes.
$appPath = Join-Path $ProjectRoot "backend\\src\\palwakf_local_agents\\app.py"
$appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$importPattern = 'from \.local_agent_core import mount_local_agent_core'
$mountPattern = 'mount_local_agent_core\(app,\s*project_root\s*=\s*PROJECT_ROOT\)'
$importCount = [regex]::Matches($appText, $importPattern).Count
$mountCount = [regex]::Matches($appText, $mountPattern).Count
if ($importCount -ne 1) { $failures += "LOCAL_AGENT_CORE_IMPORT_COUNT_INVALID=$importCount" }
if ($mountCount -ne 1) { $failures += "LOCAL_AGENT_CORE_MOUNT_COUNT_INVALID=$mountCount" }

$pilotPath = Join-Path $ProjectRoot "config\\local_agent_model_pilot_v1.json"
$pilotContract = "NOT_PRESENT"
try {
  $pilot = Get-Content -LiteralPath $pilotPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($pilot.enabled -eq $false -and $pilot.provider -eq "ollama_local_only" -and $pilot.external_network -eq "NONE") {
    $pilotContract = "DISABLED_LOCAL_ONLY_CONTRACT_MATCH"
  }
  else {
    $pilotContract = "PRESENT_BUT_CONTRACT_MISMATCH"
    $failures += "PILOT_CONFIG_CONTRACT_INVALID"
  }
}
catch {
  $pilotContract = "PRESENT_BUT_INVALID_JSON"
  $failures += "PILOT_CONFIG_INVALID_JSON"
}

$governmentRoot = Join-Path $ProjectRoot "workspaces\\palwakf_government"
$governmentState = if (Test-Path -LiteralPath $governmentRoot -PathType Container) { "PRESENT_UNCHANGED" } else { "MISSING_UNEXPECTED" }
if ($governmentState -ne "PRESENT_UNCHANGED") { $failures += "GOVERNMENT_WORKSPACE_ROOT_MISSING" }

$bootstrapRows = @()
$bootstrapIds = @("personal_development", "commercial_projects", "research_learning")
foreach ($workspaceId in $bootstrapIds) {
  $workspaceRoot = Join-Path $ProjectRoot ("workspaces\\" + $workspaceId)
  $manifestPath = Join-Path $workspaceRoot "workspace_manifest.json"
  $rootExists = Test-Path -LiteralPath $workspaceRoot
  $manifestExists = Test-Path -LiteralPath $manifestPath -PathType Leaf
  $state = "ABSENT_EXPECTED_PREIMAGE"

  if ($rootExists -or $manifestExists) {
    $state = "UNEXPECTED_EXISTING_WORKSPACE_PATH"
    $failures += "BOOTSTRAP_TARGET_ALREADY_EXISTS=$workspaceId"
  }

  $templatePath = Join-Path $PackageRoot ("candidate\\bootstrap_manifests\\" + $workspaceId + "\\workspace_manifest.json")
  $templateHash = (Get-FileHash -LiteralPath $templatePath -Algorithm SHA256).Hash

  $bootstrapRows += [pscustomobject]@{
    WorkspaceId = $workspaceId
    ProfileId = [string](@($matrix.workspaces | Where-Object { $_.workspace_id -eq $workspaceId })[0].profile_id)
    State = $state
    TemplateSHA256 = $templateHash
    TargetRoot = ("workspaces/" + $workspaceId)
    TargetManifest = ("workspaces/" + $workspaceId + "/workspace_manifest.json")
  }
}

$manifestDirectory = Join-Path $env:TEMP ("multi_workspace_agent_capability_expansion_v1_bootstrap_preflight_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
$manifestPath = Join-Path $manifestDirectory "preflight_manifest.json"

$manifest = [ordered]@{
  contract = "MEGA_BATCH_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_BOOTSTRAP_V1"
  captured_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot
  source_baseline = $sourceRows
  local_agent_core_import_count = $importCount
  local_agent_core_mount_count = $mountCount
  pilot_config_contract = $pilotContract
  government_workspace_state = $governmentState
  bootstrap_targets = $bootstrapRows
  failure_count = $failures.Count
  failures = $failures
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

"===== MULTI-WORKSPACE AGENT CAPABILITY EXPANSION V1 BOOTSTRAP PREFLIGHT ====="
$sourceRows | Format-Table RelativePath, State, ActualHash -AutoSize
$bootstrapRows | Format-Table WorkspaceId, ProfileId, State, TargetRoot, TargetManifest -AutoSize
"LOCAL_AGENT_CORE_IMPORT_COUNT=$importCount"
"LOCAL_AGENT_CORE_MOUNT_COUNT=$mountCount"
"PILOT_CONFIG_SECURITY_CONTRACT=$pilotContract"
"GOVERNMENT_WORKSPACE_ROOT_STATE=$governmentState"
"PREFLIGHT_MANIFEST=$manifestPath"
"PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
"PROJECT_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"SHELL_EXECUTION=NONE"
"GIT_WRITE=NONE"
"PROJECT_FILE_WRITE=NONE"
"EXTERNAL_NETWORK=NONE"

if ($failures.Count -eq 0) {
  "PREFLIGHT_RESULT=PASS"
}
else {
  "PREFLIGHT_RESULT=FAIL"
  "PREFLIGHT_FAILURES=$($failures -join ';')"
}
