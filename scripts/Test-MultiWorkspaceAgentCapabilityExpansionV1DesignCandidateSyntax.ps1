[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = "Stop"

$required = @(
  "README_AR.md",
  "MANIFEST_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1.md",
  "VALIDATION_REPORT_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1.md",
  "docs\ARCHITECTURE_AND_GOVERNANCE_AR.md",
  "docs\BASELINE_BINDING_PLAN_AR.md",
  "candidate\config\workspace_capability_matrix_v1.json",
  "scripts\Test-MultiWorkspaceAgentCapabilityExpansionV1DesignCandidateSyntax.ps1",
  "scripts\Test-MultiWorkspaceAgentCapabilityExpansionV1Baseline.ps1"
)

foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "CANDIDATE_REQUIRED_FILE_MISSING=$relative"
  }
}

$scriptFiles = @(
  "scripts\Test-MultiWorkspaceAgentCapabilityExpansionV1DesignCandidateSyntax.ps1",
  "scripts\Test-MultiWorkspaceAgentCapabilityExpansionV1Baseline.ps1"
)

foreach ($relative in $scriptFiles) {
  $path = Join-Path $PackageRoot $relative
  [void][scriptblock]::Create((Get-Content -LiteralPath $path -Raw -Encoding UTF8))
}

$configPath = Join-Path $PackageRoot "candidate\config\workspace_capability_matrix_v1.json"
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

$expectedWorkspaceIds = @(
  "palwakf_government",
  "personal_development",
  "commercial_projects",
  "research_learning"
)
$workspaceIds = @($config.workspaces | ForEach-Object { [string]$_.workspace_id } | Sort-Object -Unique)

if (@(Compare-Object -ReferenceObject $expectedWorkspaceIds -DifferenceObject $workspaceIds).Count -ne 0) {
  throw "WORKSPACE_CAPABILITY_MATRIX_IDS_INVALID"
}

$global = $config.global_defaults
$securityContractPass = (
  $global.model_execution -eq "NONE" -and
  $global.shell_execution -eq "NONE" -and
  $global.git_write -eq "NONE" -and
  $global.project_file_write -eq "NONE" -and
  $global.deployment -eq "NONE" -and
  $global.external_network -eq "NONE" -and
  $global.cross_workspace_access -eq "DENY" -and
  $global.human_review -eq "MANDATORY"
)

if (-not $securityContractPass) {
  throw "GLOBAL_SECURITY_CONTRACT_INVALID"
}

$commercial = @($config.workspaces | Where-Object { $_.workspace_id -eq "commercial_projects" })[0]
if ($null -eq $commercial -or $commercial.required_context -notcontains "client_id" -or $commercial.required_context -notcontains "project_id") {
  throw "COMMERCIAL_CLIENT_ISOLATION_CONTRACT_INVALID"
}

"CANDIDATE_PACKAGE_INVENTORY=PASS"
"CANDIDATE_POWERSHELL_PARSE=PASS"
"CANDIDATE_WORKSPACE_MATRIX_JSON=PASS"
"CANDIDATE_GLOBAL_SECURITY_CONTRACT=PASS"
"CANDIDATE_CLIENT_ISOLATION_CONTRACT=PASS"
"CANDIDATE_SYNTAX_RESULT=PASS"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PROJECT_MUTATION=NONE"
