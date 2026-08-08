[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @(
  'scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1',
  'scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1',
  'scripts\Test-ReadOnlyPilotActiveStateV1.ps1',
  'scripts\Test-ReadOnlyPilotLifecycleClosureV1.ps1',
  'scripts\Test-ReadOnlyPilotLifecycleClosurePackageSyntaxV1.ps1',
  'scripts\Test-ReadOnlyPilotLifecycleClosurePreflightV1.ps1',
  'scripts\Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1',
  'task_contracts\READ_ONLY_PILOT_HUMAN_REVIEW_DECISION_V1.json',
  'governance\read_only_pilot_lifecycle_closure\READ_ONLY_PILOT_HUMAN_REVIEW_AND_ARCHIVE_POLICY_V1.md',
  'governance\read_only_pilot_lifecycle_closure\DECISION_RECORD_CONTRACT_V1.md'
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Root $_)) })
$failures = @()
if ($missing.Count -eq 0) {
  try {
    $contract = Get-Content -LiteralPath (Join-Path $Root 'task_contracts\READ_ONLY_PILOT_HUMAN_REVIEW_DECISION_V1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($contract.review_scope -ne 'READ_ONLY_PILOT_RUN_REVIEW_ONLY') { $failures += 'DECISION_CONTRACT_SCOPE_INVALID' }
    if (@($contract.allowed_decisions) -notcontains 'ACCEPTED' -or @($contract.allowed_decisions) -notcontains 'REJECTED') { $failures += 'DECISION_CONTRACT_DECISIONS_INVALID' }
    if (@($contract.forbidden_effects) -notcontains 'model_execution') { $failures += 'DECISION_CONTRACT_MODEL_EXECUTION_GUARD_MISSING' }
  } catch { $failures += 'DECISION_CONTRACT_PARSE_FAILED' }
  $installerText = Get-Content -LiteralPath (Join-Path $Root 'scripts\Install-ReadOnlyPilotLifecycleClosureV1.ps1') -Raw -Encoding UTF8
  if (-not $installerText.Contains('INSTALL_BACKUP_STRATEGY=PREIMAGE_COPY_OF_EXISTING_TARGETS') -or -not $installerText.Contains('install_preimage_manifest.json')) { $failures += 'INSTALL_BACKUP_INTEGRITY_GUARD_MISSING' }
  $reviewText = Get-Content -LiteralPath (Join-Path $Root 'scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1') -Raw -Encoding UTF8
  if (-not $reviewText.Contains('EVIDENCE_MANIFEST_OUTSIDE_PROJECT_ROOT')) { $failures += 'REVIEW_MANIFEST_ROOT_GUARD_MISSING' }
  $archiveText = Get-Content -LiteralPath (Join-Path $Root 'scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1') -Raw -Encoding UTF8
  if (-not $archiveText.Contains('REVIEW_ARTIFACT_HASH_MISMATCH')) { $failures += 'ARCHIVE_HASH_REVALIDATION_GUARD_MISSING' }
  $evalText = Get-Content -LiteralPath (Join-Path $Root 'scripts\Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1') -Raw -Encoding UTF8
  if (-not $evalText.Contains('EVAL_BAD_ROOT_INSIDE_TEMP_ROOT_FORBIDDEN') -or -not $evalText.Contains('NEGATIVE_FIXTURE_COPY_OUTSIDE_TEMP_ROOT')) { $failures += 'EVAL_RECURSIVE_COPY_GUARD_MISSING' }
}
"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$([string]::Join(';',$missing))"
"VALIDATION_FAILURE_COUNT=$($failures.Count)"
"VALIDATION_FAILURES=$([string]::Join(';',$failures))"
'CORE_RUNTIME_MUTATION=NONE'; 'CORE_11_LINE_CONTRACT_MUTATION=NONE'; 'REGISTRY_MUTATION=NONE'; 'MODEL_EXECUTION=NONE'; 'PLATFORM_MUTATION=NONE'; 'DATABASE_ACCESS=NONE'; 'GIT_WRITE=NONE'; 'DEPLOYMENT=NONE'; 'SECRETS_ACCESS=NONE'; 'MEMORY_WRITE=NONE'
if ($missing.Count -eq 0 -and $failures.Count -eq 0) { 'FINAL_RESULT=PASS'; exit 0 }
'FINAL_RESULT=FAIL'; exit 1
