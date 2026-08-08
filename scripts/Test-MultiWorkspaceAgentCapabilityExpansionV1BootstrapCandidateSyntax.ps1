[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = "Stop"

$required = @(
  "README_AR.md",
  "APPLY_GUIDE_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_BOOTSTRAP_AR.md",
  "MANIFEST_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_BOOTSTRAP.md",
  "VALIDATION_REPORT_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_BOOTSTRAP.md",
  "docs\\BOOTSTRAP_GOVERNANCE_AR.md",
  "candidate\\config\\workspace_capability_matrix_v1.json",
  "candidate\\accepted_baseline_hashes_v1.json",
  "candidate\\repair_scope.json",
  "candidate\\bootstrap_manifests\\personal_development\\workspace_manifest.json",
  "candidate\\bootstrap_manifests\\commercial_projects\\workspace_manifest.json",
  "candidate\\bootstrap_manifests\\research_learning\\workspace_manifest.json",
  "scripts\\Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapCandidateSyntax.ps1",
  "scripts\\Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapPreflight.ps1",
  "scripts\\Install-MultiWorkspaceAgentCapabilityExpansionV1Bootstrap.ps1",
  "PACKAGE_INVENTORY.json"
)

foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "CANDIDATE_REQUIRED_FILE_MISSING=$relative"
  }
}

$inventoryPath = Join-Path $PackageRoot "PACKAGE_INVENTORY.json"
$inventory = Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$inventoryFailures = @()

foreach ($item in @($inventory.files)) {
  $filePath = Join-Path $PackageRoot ([string]$item.relative_path)
  if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
    $inventoryFailures += "MISSING=$($item.relative_path)"
    continue
  }
  $actual = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash
  if ($actual -ne [string]$item.sha256) {
    $inventoryFailures += "HASH_MISMATCH=$($item.relative_path)"
  }
}

if ($inventoryFailures.Count -gt 0) {
  throw "CANDIDATE_PACKAGE_INVENTORY_INVALID=$($inventoryFailures -join ';')"
}

$scriptFiles = @(
  "scripts\\Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapCandidateSyntax.ps1",
  "scripts\\Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapPreflight.ps1",
  "scripts\\Install-MultiWorkspaceAgentCapabilityExpansionV1Bootstrap.ps1"
)

foreach ($relative in $scriptFiles) {
  $path = Join-Path $PackageRoot $relative
  [void][scriptblock]::Create((Get-Content -LiteralPath $path -Raw -Encoding UTF8))
}

$preflightPath = Join-Path $PackageRoot "scripts\\Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapPreflight.ps1"
$preflightText = Get-Content -LiteralPath $preflightPath -Raw -Encoding UTF8
if (-not $preflightText.Contains('$importPattern = ''from \.local_agent_core import mount_local_agent_core''')) {
  throw "PREFLIGHT_IMPORT_ANCHOR_REPAIR_MISSING"
}
if (-not $preflightText.Contains('$mountPattern = ''mount_local_agent_core\(app,\s*project_root\s*=\s*PROJECT_ROOT\)''')) {
  throw "PREFLIGHT_MOUNT_ANCHOR_REPAIR_MISSING"
}
if ($preflightText.Contains('$importPattern = ''from \\.local_agent_core import mount_local_agent_core''')) {
  throw "PREFLIGHT_LEGACY_DOUBLE_BACKSLASH_IMPORT_PATTERN_PRESENT"
}
$repairScopePath = Join-Path $PackageRoot "candidate\\repair_scope.json"
$repairScope = Get-Content -LiteralPath $repairScopePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($repairScope.repair_scope -ne "PREFLIGHT_ANCHOR_REGEX_ONLY" -or $repairScope.project_source_mutation -ne "NONE") {
  throw "REPAIR_SCOPE_CONTRACT_INVALID"
}

$matrixPath = Join-Path $PackageRoot "candidate\\config\\workspace_capability_matrix_v1.json"
$matrix = Get-Content -LiteralPath $matrixPath -Raw -Encoding UTF8 | ConvertFrom-Json
$expected = @("palwakf_government", "personal_development", "commercial_projects", "research_learning")
$actual = @($matrix.workspaces | ForEach-Object { [string]$_.workspace_id } | Sort-Object -Unique)

if (@(Compare-Object -ReferenceObject $expected -DifferenceObject $actual).Count -ne 0) {
  throw "WORKSPACE_MATRIX_IDS_INVALID"
}

$global = $matrix.global_defaults
$globalPass = (
  $global.model_execution -eq "NONE" -and
  $global.pilot_execution -eq "NOT_EXECUTED" -and
  $global.shell_execution -eq "NONE" -and
  $global.git_write -eq "NONE" -and
  $global.project_file_write -eq "NONE" -and
  $global.deployment -eq "NONE" -and
  $global.external_network -eq "NONE" -and
  $global.cross_workspace_access -eq "DENY" -and
  $global.human_review -eq "MANDATORY"
)

if (-not $globalPass) {
  throw "GLOBAL_SECURITY_CONTRACT_INVALID"
}

$commercial = @($matrix.workspaces | Where-Object { $_.workspace_id -eq "commercial_projects" })[0]
if ($null -eq $commercial -or $commercial.required_context -notcontains "client_id" -or $commercial.required_context -notcontains "project_id") {
  throw "COMMERCIAL_CONTEXT_CONTRACT_INVALID"
}

$bootstrapIds = @("personal_development", "commercial_projects", "research_learning")
foreach ($workspaceId in $bootstrapIds) {
  $path = Join-Path $PackageRoot ("candidate\\bootstrap_manifests\\" + $workspaceId + "\\workspace_manifest.json")
  $manifest = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
  $valid = (
    $manifest.workspace_id -eq $workspaceId -and
    $manifest.lifecycle_state -eq "BOOTSTRAPPED_PREPARE_ONLY" -and
    $manifest.workspace_storage_initialized -eq $false -and
    $manifest.model_execution -eq "NONE" -and
    $manifest.shell_execution -eq "NONE" -and
    $manifest.git_write -eq "NONE" -and
    $manifest.project_file_write -eq "NONE" -and
    $manifest.external_network -eq "NONE" -and
    $manifest.cross_workspace_access -eq "DENY" -and
    $manifest.human_review -eq "MANDATORY"
  )
  if (-not $valid) {
    throw "BOOTSTRAP_MANIFEST_SECURITY_CONTRACT_INVALID=$workspaceId"
  }
}

"CANDIDATE_PACKAGE_INVENTORY=PASS"
"CANDIDATE_POWERSHELL_PARSE=PASS"
"CANDIDATE_PREFLIGHT_ANCHOR_REPAIR_CONTRACT=PASS"
"CANDIDATE_REPAIR_SCOPE_CONTRACT=PASS"
"CANDIDATE_WORKSPACE_MATRIX_JSON=PASS"
"CANDIDATE_GLOBAL_SECURITY_CONTRACT=PASS"
"CANDIDATE_COMMERCIAL_CONTEXT_CONTRACT=PASS"
"CANDIDATE_BOOTSTRAP_MANIFEST_CONTRACT=PASS"
"CANDIDATE_SYNTAX_RESULT=PASS"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PROJECT_MUTATION=NONE"
