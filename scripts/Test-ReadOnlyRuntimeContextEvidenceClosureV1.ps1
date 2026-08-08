[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @(
  'governance/read_only_runtime_context_evidence/READ_ONLY_RUNTIME_CONTEXT_POLICY_V1.md',
  'governance/read_only_runtime_context_evidence/UNTRUSTED_REFERENCE_CONTENT_POLICY_V1.md',
  'governance/read_only_runtime_context_evidence/MODEL_OUTPUT_ACCEPTANCE_POLICY_V1.md',
  'task_contracts/EVIDENCE_MANIFEST_SCHEMA_V1.json',
  'task_contracts/READ_ONLY_RUNTIME_CONTEXT_SCHEMA_V1.json',
  'task_contracts/MODEL_OUTPUT_CONTRACT_V1.json',
  'task_contracts/READ_ONLY_CONTEXT_TASK_INTAKE_SCHEMA_V1.json',
  'templates/READ_ONLY_CONTEXT_EVIDENCE_REPORT_AR_V1.md',
  'runtime/ReadOnlyRuntimeContextEvidenceV1.psm1',
  'reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md',
  'tasks/templates/PILOT_READ_ONLY_CONTEXT_EVIDENCE_TASK_V1.json',
  'scripts/New-ReadOnlyEvidenceTaskV1.ps1',
  'scripts/New-ReadOnlyEvidencePilotV1.ps1',
  'scripts/Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts/Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1',
  'output/evidence_manifests','output/read_only_context_runs','runtime/context'
)
$missing = @()
foreach ($relative in $required) { if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) { $missing += $relative } }
$contractPath = Join-Path $Root 'task_contracts/MODEL_OUTPUT_CONTRACT_V1.json'
$contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$requiredKeys = @($contract.required_keys)
$pilotPath = Join-Path $Root 'tasks/templates/PILOT_READ_ONLY_CONTEXT_EVIDENCE_TASK_V1.json'
$pilot = Get-Content -LiteralPath $pilotPath -Raw -Encoding UTF8 | ConvertFrom-Json
$invalidPilotPaths = @($pilot.allowed_reference_paths | Where-Object { $_ -notmatch '^reference_sources/approved/' })
"REQUIRED_ITEM_COUNT=$($required.Count)"
"MISSING_ITEM_COUNT=$($missing.Count)"
"MODEL_OUTPUT_REQUIRED_KEY_COUNT=$($requiredKeys.Count)"
"PILOT_REFERENCE_PATH_COUNT=$(@($pilot.allowed_reference_paths).Count)"
"PILOT_INVALID_REFERENCE_PATH_COUNT=$($invalidPilotPaths.Count)"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
if ($missing.Count -eq 0 -and $requiredKeys.Count -eq 11 -and $invalidPilotPaths.Count -eq 0) { 'FINAL_RESULT=PASS'; exit 0 }
'MISSING_OR_INVALID_ITEMS='
$missing + $invalidPilotPaths | ForEach-Object { $_ }
'FINAL_RESULT=FAIL'
exit 1
