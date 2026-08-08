[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @(
  'scripts\Test-StructuredAnalysisPayloadFoundationV1.ps1',
  'scripts\Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1',
  'tasks\approved\PILOT_READ_ONLY_CONTEXT_EVIDENCE_001.json',
  'output\read_only_context_runs\RUN-20260627142818-PILOT_READ_ONLY_CONTEXT_EVIDENCE_001-coordinator.canonical.txt',
  'output\read_only_context_runs\RUN-20260627142818-PILOT_READ_ONLY_CONTEXT_EVIDENCE_001-coordinator.raw.txt',
  'output\read_only_context_runs\RUN-20260627142818-PILOT_READ_ONLY_CONTEXT_EVIDENCE_001-coordinator.report.md',
  'output\evidence_manifests\EVM-20260627112818-PILOT_READ_ONLY_CONTEXT_EVIDENCE_001.json'
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Root $_)) })
$failures = @()
if ($missing.Count -eq 0) {
  $task = Get-Content -LiteralPath (Join-Path $Root 'tasks\approved\PILOT_READ_ONLY_CONTEXT_EVIDENCE_001.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($task.status -ne 'APPROVED_FOR_READ_ONLY_RUN') { $failures += "EXISTING_PILOT_STATUS_UNEXPECTED=$($task.status)" }
  if ($task.requested_agent -ne 'coordinator') { $failures += "EXISTING_PILOT_AGENT_UNEXPECTED=$($task.requested_agent)" }
  $newPending = Join-Path $Root 'tasks\inbox\SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json'
  if (-not (Test-Path -LiteralPath $newPending)) { $failures += 'NEW_PENDING_PILOT_NOT_FOUND' }
}
"REQUIRED_BASELINE_FILE_COUNT=$($required.Count)"
"MISSING_BASELINE_FILE_COUNT=$($missing.Count)"
"MISSING_BASELINE_FILES=$([string]::Join(';',$missing))"
"PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
"PREFLIGHT_FAILURES=$([string]::Join(';',$failures))"
'BASELINE_RECHECK_REQUIRED=YES'; 'CORE_RUNTIME_MUTATION=NONE'; 'CORE_11_LINE_CONTRACT_MUTATION=NONE'; 'REGISTRY_MUTATION=NONE'; 'MODEL_EXECUTION=NONE'; 'PLATFORM_MUTATION=NONE'; 'DATABASE_ACCESS=NONE'; 'GIT_WRITE=NONE'; 'DEPLOYMENT=NONE'; 'SECRETS_ACCESS=NONE'; 'MEMORY_WRITE=NONE'
if ($missing.Count -eq 0 -and $failures.Count -eq 0) { 'PREFLIGHT_RESULT=PASS'; exit 0 }
'PREFLIGHT_RESULT=FAIL'; exit 1
