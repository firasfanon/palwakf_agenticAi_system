[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [switch]$PackageRuntimeSelfTest
)

$ErrorActionPreference = "Stop"

function Add-Failure {
  param([System.Collections.Generic.List[string]]$List, [string]$Value)
  [void]$List.Add($Value)
}

foreach ($requiredDirectory in @($PackageRoot, $ProjectRoot)) {
  if (-not (Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
    throw ("REQUIRED_DIRECTORY_NOT_FOUND={0}" -f $requiredDirectory)
  }
}

$contractPath = Join-Path $PackageRoot "contracts\master_batch_contract_v1.json"
if (-not (Test-Path -LiteralPath $contractPath -PathType Leaf)) {
  throw "MASTER_CONTRACT_NOT_FOUND"
}

$contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$packageId = [string]$contract.package_id
$schemaVersion = [string]$contract.manifest_binding_schema_version
if ([string]::IsNullOrWhiteSpace($packageId) -or [string]::IsNullOrWhiteSpace($schemaVersion)) {
  throw "MASTER_CONTRACT_BINDING_FIELDS_MISSING"
}

$failures = New-Object System.Collections.Generic.List[string]
$sourceInventory = New-Object System.Collections.Generic.List[object]
$baselineCheck = if ($PackageRuntimeSelfTest) { "SKIPPED_FOR_PACKAGE_RUNTIME_SELF_TEST" } else { "PASS" }

foreach ($property in $contract.baseline_anchors.files.PSObject.Properties) {
  $relativePath = [string]$property.Name
  $expectedHash = [string]$property.Value
  $absolutePath = Join-Path $ProjectRoot $relativePath
  $exists = Test-Path -LiteralPath $absolutePath -PathType Leaf
  $actualHash = $null
  $state = "MISSING"

  if (-not $exists) {
    Add-Failure $failures ("BASELINE_FILE_MISSING={0}" -f $relativePath)
  }
  else {
    $actualHash = (Get-FileHash -LiteralPath $absolutePath -Algorithm SHA256).Hash
    if ($PackageRuntimeSelfTest) {
      $state = "PRESENT_FOR_PACKAGE_RUNTIME_SELF_TEST"
    }
    elseif ($actualHash -eq $expectedHash) {
      $state = "TARGET_EQUALS_ACCEPTED_BASELINE"
    }
    else {
      $state = "TARGET_HASH_MISMATCH"
      $baselineCheck = "FAIL"
      Add-Failure $failures ("BASELINE_HASH_MISMATCH={0}" -f $relativePath)
    }
  }

  [void]$sourceInventory.Add([pscustomobject]@{
    relative_path = $relativePath
    expected_sha256 = $expectedHash
    actual_sha256 = $actualHash
    state = $state
  })
}

$pilotPath = Join-Path $ProjectRoot "config\local_agent_model_pilot_v1.json"
$pilotContract = "INVALID"
try {
  $pilot = Get-Content -LiteralPath $pilotPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($pilot.enabled -eq $false -and $pilot.provider -eq "ollama_local_only" -and $pilot.external_network -eq "NONE") {
    $pilotContract = "DISABLED_LOCAL_ONLY_CONTRACT_MATCH"
  }
  else {
    Add-Failure $failures "PILOT_CONFIG_CONTRACT_INVALID"
  }
}
catch {
  Add-Failure $failures "PILOT_CONFIG_INVALID_JSON"
}

$governmentRoot = Join-Path $ProjectRoot "workspaces\palwakf_government"
$governmentManifest = Join-Path $governmentRoot "workspace_manifest.json"
$governmentSqlite = Join-Path $governmentRoot "local_agent_core.sqlite"

if (-not (Test-Path -LiteralPath $governmentRoot -PathType Container)) {
  Add-Failure $failures "GOVERNMENT_WORKSPACE_ROOT_MISSING"
}

$governmentSqliteState = if (Test-Path -LiteralPath $governmentSqlite -PathType Leaf) { "PRESENT" } else { "ABSENT" }
if ($governmentSqliteState -ne "PRESENT") {
  Add-Failure $failures "GOVERNMENT_SQLITE_REQUIRED_PRESENT_BUT_ABSENT"
}

$governmentManifestState = "MISSING_EXPECTED_P0_PREIMAGE"
if (Test-Path -LiteralPath $governmentManifest -PathType Leaf) {
  $governmentManifestState = "PRESENT_POLICY_BINDING_INVALID"
  try {
    $governmentRaw = Get-Content -LiteralPath $governmentManifest -Raw -Encoding UTF8
    $null = $governmentRaw | ConvertFrom-Json
    $governmentBindingValid = (
      $governmentRaw -match [regex]::Escape("palwakf_government") -and
      $governmentRaw -match [regex]::Escape("government_strict_v1")
    )
    if ($governmentBindingValid) {
      $governmentManifestState = "PRESENT_VERIFIED_IDEMPOTENT"
    }
    else {
      Add-Failure $failures "GOVERNMENT_MANIFEST_POLICY_BINDING_INVALID"
    }
  }
  catch {
    Add-Failure $failures "GOVERNMENT_MANIFEST_INVALID_JSON"
  }
}

$workspaceProfiles = @{
  personal_development = "developer_controlled_v1"
  commercial_projects = "client_isolated_v1"
  research_learning = "research_read_prepare_v1"
}
$workspaceStates = New-Object System.Collections.Generic.List[object]
foreach ($workspaceId in @("personal_development", "commercial_projects", "research_learning")) {
  $workspaceRoot = Join-Path $ProjectRoot ("workspaces\{0}" -f $workspaceId)
  $manifestPath = Join-Path $workspaceRoot "workspace_manifest.json"
  $rootExists = Test-Path -LiteralPath $workspaceRoot -PathType Container
  $manifestExists = Test-Path -LiteralPath $manifestPath -PathType Leaf
  $sqliteCount = 0
  $profileBound = $false

  if ($rootExists) {
    $sqliteCount = @(Get-ChildItem -LiteralPath $workspaceRoot -Filter "*.sqlite" -File -Recurse -Force -ErrorAction SilentlyContinue).Count
  }
  if ($manifestExists) {
    try {
      $rawManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
      $null = $rawManifest | ConvertFrom-Json
      $profileBound = (
        $rawManifest -match [regex]::Escape($workspaceId) -and
        $rawManifest -match [regex]::Escape($workspaceProfiles[$workspaceId])
      )
    }
    catch {
      $profileBound = $false
    }
  }

  if (-not $rootExists) { Add-Failure $failures ("WORKSPACE_ROOT_MISSING={0}" -f $workspaceId) }
  if (-not $manifestExists) { Add-Failure $failures ("WORKSPACE_MANIFEST_MISSING={0}" -f $workspaceId) }
  if (-not $profileBound) { Add-Failure $failures ("WORKSPACE_PROFILE_BINDING_INVALID={0}" -f $workspaceId) }
  if ($sqliteCount -ne 0) { Add-Failure $failures ("WORKSPACE_SQLITE_UNEXPECTED={0}:{1}" -f $workspaceId, $sqliteCount) }

  [void]$workspaceStates.Add([pscustomobject]@{
    workspace_id = $workspaceId
    workspace_root_exists = $rootExists
    manifest_exists = $manifestExists
    profile_bound = $profileBound
    sqlite_count = $sqliteCount
  })
}

$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$contractHash = (Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash
$preflightScriptHash = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
$outputDirectory = Join-Path $env:TEMP ("mega_batch_01_to_06_unified_preflight_binding_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$manifestOutputPath = Join-Path $outputDirectory "baseline_preflight_manifest.json"

$report = [pscustomobject]@{
  contract = [string]$contract.contract
  package_id = $packageId
  manifest_binding_schema_version = $schemaVersion
  captured_at = (Get-Date).ToString("o")
  project_root = $resolvedProjectRoot
  contract_sha256 = $contractHash
  preflight_script_name = (Split-Path -Leaf $PSCommandPath)
  preflight_script_sha256 = $preflightScriptHash
  baseline_hash_check = $baselineCheck
  government_manifest_state = $governmentManifestState
  government_sqlite_state = $governmentSqliteState
  pilot_config_contract = $pilotContract
  source_inventory = @($sourceInventory.ToArray())
  workspace_states = @($workspaceStates.ToArray())
  preflight_failure_count = $failures.Count
  preflight_failures = @($failures.ToArray())
  project_mutation = "NONE"
  model_execution = "NONE"
  pilot_execution = "NOT_EXECUTED"
  shell_execution = "NONE"
  git_write = "NONE"
  external_network = "NONE"
}
$report | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $manifestOutputPath -Encoding UTF8

"===== MEGA BATCH 01 TO 06 UNIFIED BASELINE PREFLIGHT ====="
$sourceInventory | Format-Table relative_path, state, actual_sha256 -AutoSize
$workspaceStates | Format-Table workspace_id, workspace_root_exists, manifest_exists, profile_bound, sqlite_count -AutoSize
("PREFLIGHT_PACKAGE_ID={0}" -f $packageId)
("PREFLIGHT_CONTRACT_SHA256={0}" -f $contractHash)
("PREFLIGHT_SCRIPT_SHA256={0}" -f $preflightScriptHash)
("PREFLIGHT_BASELINE_HASH_CHECK={0}" -f $baselineCheck)
("GOVERNMENT_MANIFEST_STATE={0}" -f $governmentManifestState)
("GOVERNMENT_SQLITE_STATE={0}" -f $governmentSqliteState)
("PREFLIGHT_MANIFEST={0}" -f $manifestOutputPath)
("PREFLIGHT_FAILURE_COUNT={0}" -f $failures.Count)
"PROJECT_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"SHELL_EXECUTION=NONE"
"GIT_WRITE=NONE"
"EXTERNAL_NETWORK=NONE"

if ($failures.Count -gt 0) {
  "PREFLIGHT_RESULT=FAIL"
  ("PREFLIGHT_FAILURES={0}" -f ($failures -join ';'))
  throw "MEGA_BATCH_01_TO_06_UNIFIED_PREFLIGHT_FAILED"
}
"PREFLIGHT_RESULT=PASS"
