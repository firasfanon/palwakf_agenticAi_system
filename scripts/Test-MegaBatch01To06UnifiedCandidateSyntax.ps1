[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = "Stop"
$failures = New-Object System.Collections.Generic.List[string]

$requiredFiles = @(
  "README_AR.md",
  "MANIFEST_MEGA_BATCH_01_TO_06_UNIFIED_GOVERNED_CAPABILITY_FOUNDATION_V1.md",
  "RUN_GUIDE_PREFLIGHT_AND_MANIFEST_BINDING_REPAIR_AR.md",
  "EXECUTION_MATRIX_AR.md",
  "IMPROVEMENT_NOTES_AFTER_ACCEPTANCE_AR.md",
  "contracts\master_batch_contract_v1.json",
  "candidate\accepted_baseline_hashes_v1.json",
  "scripts\Invoke-MegaBatch01To06UnifiedBaselinePreflight.ps1",
  "scripts\Invoke-MegaBatch01To06UnifiedPlanningWhatIf.ps1",
  "scripts\Invoke-MegaBatch01To06UnifiedCandidateReadiness.ps1",
  "PACKAGE_INVENTORY.json"
)

foreach ($relativePath in $requiredFiles) {
  $candidatePath = Join-Path $PackageRoot $relativePath
  if (-not (Test-Path -LiteralPath $candidatePath -PathType Leaf)) {
    [void]$failures.Add(("MISSING_REQUIRED_FILE={0}" -f $relativePath))
  }
}

$inventoryHashPass = $true
$inventoryPath = Join-Path $PackageRoot "PACKAGE_INVENTORY.json"
try {
  $inventory = Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($entry in $inventory.files) {
    $entryPath = Join-Path $PackageRoot ([string]$entry.path)
    if (-not (Test-Path -LiteralPath $entryPath -PathType Leaf)) {
      $inventoryHashPass = $false
      [void]$failures.Add(("INVENTORY_FILE_MISSING={0}" -f [string]$entry.path))
      continue
    }
    $actualHash = (Get-FileHash -LiteralPath $entryPath -Algorithm SHA256).Hash
    if ($actualHash -ne [string]$entry.sha256) {
      $inventoryHashPass = $false
      [void]$failures.Add(("INVENTORY_HASH_MISMATCH={0}" -f [string]$entry.path))
    }
  }
}
catch {
  $inventoryHashPass = $false
  [void]$failures.Add(("PACKAGE_INVENTORY_INVALID={0}" -f $_.Exception.Message))
}

$scriptFiles = @(Get-ChildItem -LiteralPath (Join-Path $PackageRoot "scripts") -Filter "*.ps1" -File -Recurse)
$parseErrorCount = 0
$unsafeInterpolationCount = 0
foreach ($scriptFile in $scriptFiles) {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($scriptFile.FullName, [ref]$tokens, [ref]$errors)
  if ($errors.Count -gt 0) {
    $parseErrorCount += $errors.Count
    foreach ($error in $errors) {
      [void]$failures.Add(("POWERSHELL_PARSE_ERROR={0}:{1}" -f $scriptFile.Name, $error.Message))
    }
  }
  $scriptText = Get-Content -LiteralPath $scriptFile.FullName -Raw -Encoding UTF8
  $scanText = $scriptText -replace '\$env:', ''
  $unsafeMatches = [regex]::Matches($scanText, '\$[A-Za-z_][A-Za-z0-9_]*:')
  if ($unsafeMatches.Count -gt 0) {
    $unsafeInterpolationCount += $unsafeMatches.Count
    [void]$failures.Add(("UNSAFE_VARIABLE_COLON_PATTERN={0}" -f $scriptFile.Name))
  }
}

$contractValid = $false
$contractPath = Join-Path $PackageRoot "contracts\master_batch_contract_v1.json"
try {
  $contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $contractValid = (
    [string]$contract.contract -eq "MEGA_BATCH_01_TO_06_UNIFIED_GOVERNED_CAPABILITY_FOUNDATION_V1" -and
    [string]$contract.package_id -like "*PREFLIGHT_AND_MANIFEST_BINDING_REPAIR_CANDIDATE" -and
    $contract.workstreams.Count -eq 6 -and
    [string]$contract.hard_controls.default_model_execution -eq "NONE" -and
    [string]$contract.hard_controls.external_network -eq "NONE" -and
    [string]$contract.manifest_binding_schema_version -eq "1.0"
  )
  if (-not $contractValid) { [void]$failures.Add("MASTER_CONTRACT_INVALID") }
}
catch {
  [void]$failures.Add(("MASTER_CONTRACT_JSON_INVALID={0}" -f $_.Exception.Message))
}

$runtimeSelfTestPass = $false
$runtimeTestRoot = $null
$runtimeManifestPath = $null
try {
  $runtimeTestRoot = Join-Path $env:TEMP ("mega_batch_01_to_06_runtime_self_test_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
  New-Item -ItemType Directory -Path $runtimeTestRoot -Force | Out-Null
  $sourcePaths = @(
    "backend\src\palwakf_local_agents\app.py",
    "backend\src\palwakf_local_agents\local_agent_core\__init__.py",
    "backend\src\palwakf_local_agents\local_agent_core\contracts.py",
    "backend\src\palwakf_local_agents\local_agent_core\policy.py",
    "backend\src\palwakf_local_agents\local_agent_core\router.py",
    "backend\src\palwakf_local_agents\local_agent_core\store.py",
    "backend\tests\test_governed_local_agent_core.py"
  )
  foreach ($sourceRelativePath in $sourcePaths) {
    $sourcePath = Join-Path $runtimeTestRoot $sourceRelativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $sourcePath) -Force | Out-Null
    Set-Content -LiteralPath $sourcePath -Value "# package runtime self test" -Encoding UTF8
  }
  $pilotPath = Join-Path $runtimeTestRoot "config\local_agent_model_pilot_v1.json"
  New-Item -ItemType Directory -Path (Split-Path -Parent $pilotPath) -Force | Out-Null
  '{"enabled":false,"provider":"ollama_local_only","external_network":"NONE"}' | Set-Content -LiteralPath $pilotPath -Encoding UTF8

  $governmentRoot = Join-Path $runtimeTestRoot "workspaces\palwakf_government"
  New-Item -ItemType Directory -Path $governmentRoot -Force | Out-Null
  New-Item -ItemType File -Path (Join-Path $governmentRoot "local_agent_core.sqlite") -Force | Out-Null

  $profiles = @{
    personal_development = "developer_controlled_v1"
    commercial_projects = "client_isolated_v1"
    research_learning = "research_read_prepare_v1"
  }
  foreach ($workspaceId in $profiles.Keys) {
    $workspaceRoot = Join-Path $runtimeTestRoot ("workspaces\{0}" -f $workspaceId)
    New-Item -ItemType Directory -Path $workspaceRoot -Force | Out-Null
    $workspaceManifest = [pscustomobject]@{ workspace_id = $workspaceId; profile_id = $profiles[$workspaceId] }
    $workspaceManifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workspaceRoot "workspace_manifest.json") -Encoding UTF8
  }

  $preflightScript = Join-Path $PackageRoot "scripts\Invoke-MegaBatch01To06UnifiedBaselinePreflight.ps1"
  $whatIfScript = Join-Path $PackageRoot "scripts\Invoke-MegaBatch01To06UnifiedPlanningWhatIf.ps1"
  $runtimePreflightOutput = @()
  try {
    $runtimePreflightOutput = @(& $preflightScript -PackageRoot $PackageRoot -ProjectRoot $runtimeTestRoot -PackageRuntimeSelfTest)
  }
  catch {
    throw ("RUNTIME_PREFLIGHT_EXECUTION_FAILED={0}" -f $_.Exception.Message)
  }
  $runtimeManifestLine = @($runtimePreflightOutput | Where-Object { $_ -is [string] -and $_ -like "PREFLIGHT_MANIFEST=*" } | Select-Object -Last 1)
  if ($runtimeManifestLine.Count -ne 1) { throw "RUNTIME_PREFLIGHT_MANIFEST_NOT_EMITTED" }
  $runtimeManifestPath = $runtimeManifestLine.Substring("PREFLIGHT_MANIFEST=".Length)
  $runtimeWhatIfOutput = @(& $whatIfScript -PackageRoot $PackageRoot -ProjectRoot $runtimeTestRoot -PreflightManifest $runtimeManifestPath -AllowPackageRuntimeSelfTest)
  $runtimeSelfTestPass = (
    ($runtimePreflightOutput -join "`n") -match "PREFLIGHT_RESULT=PASS" -and
    ($runtimeWhatIfOutput -join "`n") -match "PREFLIGHT_MANIFEST_BINDING=PASS" -and
    ($runtimeWhatIfOutput -join "`n") -match "WHATIF_STATUS=COMPLETE"
  )
  if (-not $runtimeSelfTestPass) { throw "RUNTIME_PREFLIGHT_WHATIF_EXPECTED_OUTPUT_MISSING" }
}
catch {
  [void]$failures.Add(("PREFLIGHT_WHATIF_RUNTIME_SELF_TEST_FAILED={0}" -f $_.Exception.Message))
}
finally {
  if ($runtimeManifestPath -and (Test-Path -LiteralPath $runtimeManifestPath -PathType Leaf)) {
    Remove-Item -LiteralPath (Split-Path -Parent $runtimeManifestPath) -Recurse -Force -ErrorAction SilentlyContinue
  }
  if ($runtimeTestRoot -and (Test-Path -LiteralPath $runtimeTestRoot -PathType Container)) {
    Remove-Item -LiteralPath $runtimeTestRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}

$inventoryPass = ($failures | Where-Object { $_ -like "MISSING_REQUIRED_FILE=*" }).Count -eq 0
"CANDIDATE_PACKAGE_INVENTORY=$(if ($inventoryPass) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_INVENTORY_HASHES=$(if ($inventoryHashPass) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_POWERSHELL_PARSE=$(if ($parseErrorCount -eq 0) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN=$(if ($unsafeInterpolationCount -eq 0) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_MASTER_CONTRACT=$(if ($contractValid) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_PREFLIGHT_WHATIF_RUNTIME_SELF_TEST=$(if ($runtimeSelfTestPass) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_REPAIR_SCOPE=PREFLIGHT_AND_MANIFEST_BINDING_ONLY"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PROJECT_MUTATION=NONE"
"SERVICE_START=NONE"
"EXTERNAL_NETWORK=NONE"

if ($failures.Count -gt 0) {
  ("CANDIDATE_FAILURES={0}" -f ($failures -join ';'))
  "CANDIDATE_SYNTAX_RESULT=FAIL"
  throw "MEGA_BATCH_01_TO_06_UNIFIED_REPAIR_CANDIDATE_SYNTAX_FAILED"
}
"CANDIDATE_SYNTAX_RESULT=PASS"
