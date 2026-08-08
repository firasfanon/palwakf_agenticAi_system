[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not (Test-Path -LiteralPath $Root)) {
  throw "PROJECT_ROOT_NOT_FOUND=$Root"
}

$RequiredFiles = @(
  "README_AR.md",
  "PROJECT_STATUS_AR.md",
  "agents\registry_v2.yaml",
  "governance\00_AGENT_OPERATING_CONTRACT_V2.md",
  "governance\01_AUTONOMY_RISK_APPROVAL_MATRIX_V2.md",
  "governance\03_MEMORY_EVIDENCE_LEARNING_POLICY_V2.md",
  "governance\04_PROMPT_INJECTION_AND_DATA_CLASSIFICATION_POLICY_V2.md",
  "governance\05_TOOL_GATEWAY_AND_MODEL_ROUTING_V2.md",
  "skills\registry_v1.yaml",
  "skills\task_triage\SKILL.md",
  "skills\evidence_assessment\SKILL.md",
  "skills\prompt_injection_screening\SKILL.md",
  "task_contracts\task_run_v2.schema.json",
  "task_contracts\evidence_register_v2.schema.json",
  "task_contracts\learning_candidate_v2.schema.json",
  "memory\README_AR.md",
  "evals\README_AR.md",
  "reference_sources\operating_manual\LOCAL_AGENTS_WEB_APP_AGENTIC_OPERATING_SYSTEM_v2.md"
)

$Missing = @()
foreach ($RelativePath in $RequiredFiles) {
  $FullPath = Join-Path $Root $RelativePath
  if (-not (Test-Path -LiteralPath $FullPath)) {
    $Missing += $RelativePath
  }
}

$RegistryPath = Join-Path $Root "agents\registry_v2.yaml"
$RegistryContractFound = $false
if (Test-Path -LiteralPath $RegistryPath) {
  $RegistryContractFound = Select-String -LiteralPath $RegistryPath -Pattern "agent_execution: disabled" -Quiet
}

$SkillSchemaCount = @(Get-ChildItem -LiteralPath (Join-Path $Root "skills") -Filter "output_schema.json" -Recurse -File -ErrorAction SilentlyContinue).Count

Write-Output "REQUIRED_FILE_COUNT=$($RequiredFiles.Count)"
Write-Output "MISSING_FILE_COUNT=$($Missing.Count)"
Write-Output "SKILL_OUTPUT_SCHEMA_COUNT=$SkillSchemaCount"
Write-Output "REGISTRY_EXECUTION_DISABLED=$RegistryContractFound"
Write-Output "PLATFORM_MUTATION=NONE"
Write-Output "DATABASE_ACCESS=NONE"

if ($Missing.Count -eq 0 -and $RegistryContractFound -and $SkillSchemaCount -ge 10) {
  Write-Output "FINAL_RESULT=PASS"
  exit 0
}

if ($Missing.Count -gt 0) {
  foreach ($Item in $Missing) {
    Write-Output "MISSING_FILE=$Item"
  }
}

Write-Output "FINAL_RESULT=FAIL"
exit 1
