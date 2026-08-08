[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @('scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1','scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1','scripts\Test-ReadOnlyPilotActiveStateV1.ps1')
foreach ($relative in $required) { if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) { throw "REQUIRED_PATH_NOT_FOUND=$relative" } }
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("pwf_plc_eval_" + [Guid]::NewGuid().ToString('N'))
$badRoot = $null
$results = @()
function Add-Result([string]$CaseId,[bool]$Passed,[string]$Detail) { $script:results += [pscustomobject]@{ case_id=$CaseId; passed=$Passed; detail=$Detail } }
try {
  'EVAL_STAGE=SETUP'
  foreach ($relative in @('tasks\approved','output\read_only_context_runs','output\evidence_manifests','audit')) { New-Item -ItemType Directory -Path (Join-Path $tempRoot $relative) -Force | Out-Null }
  $taskId='PLC_EVAL_TASK_001'; $runId='RUN-20260627142818-PLC_EVAL_TASK_001-coordinator'
  $task=[ordered]@{ task_id=$taskId; status='APPROVED_FOR_READ_ONLY_RUN'; requested_agent='coordinator'; risk='LOW'; autonomy='L0_READ_ONLY'; title='Eval'; description='Eval'; requested_skills=@('task_triage','evidence_assessment'); allowed_reference_paths=@('reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md') }
  $task | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $tempRoot "tasks\approved\$taskId.json") -Encoding UTF8
  $canonical=@('OUTPUT_CONTRACT_START','ROLE=coordinator','TASK_STATUS=ANALYSIS_COMPLETE','TASK_CLASS=READ_ONLY_EVIDENCE_ANALYSIS','TRUTH_SOURCE=APPROVED_REFERENCE_CONTENT_ONLY','LIVE_STATE_PROVEN=NO','MUTATION_ALLOWED=NO','EVIDENCE_STATUS=EVIDENCE_MANIFEST_USED','EVIDENCE_REFERENCE_IDS=EVD-001','UNCERTAINTY_STATUS=LIMITED_TO_REFERENCE_EVIDENCE','SECURITY_POSTURE=UNTRUSTED_REFERENCE_CONTENT_NOT_EXECUTED','NEXT_STEP=HUMAN_REVIEW_REQUIRED','OUTPUT_CONTRACT_END')
  $canonicalPath=Join-Path $tempRoot "output\read_only_context_runs\$runId.canonical.txt"; $canonical | Set-Content -LiteralPath $canonicalPath -Encoding UTF8
  'raw' | Set-Content -LiteralPath (Join-Path $tempRoot "output\read_only_context_runs\$runId.raw.txt") -Encoding UTF8
  $report=@("- Task ID: $taskId",'- Run status: PENDING_HUMAN_REVIEW','MODEL_OUTPUT_VALID=True','MODEL_OUTPUT_RAW_LINE_COUNT=11','MODEL_OUTPUT_TRAILING_LINE_COUNT=0','SYSTEM_OWNED_ENVELOPE_CREATED=True','- PLATFORM_MUTATION: NONE','- DATABASE_ACCESS: NONE','- GIT_WRITE: NONE','- DEPLOYMENT: NONE','- SECRETS_ACCESS: NONE','- MEMORY_WRITE: NONE') -join "`n"
  $report | Set-Content -LiteralPath (Join-Path $tempRoot "output\read_only_context_runs\$runId.report.md") -Encoding UTF8
  $manifest=[ordered]@{ task_id=$taskId; platform_mutation='NONE'; database_access='NONE'; git_write='NONE'; deployment='NONE'; evidence_items=@([ordered]@{evidence_id='EVD-001'}) }
  $manifestPath=Join-Path $tempRoot "output\evidence_manifests\EVM-$taskId.json"; $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
  'EVAL_STAGE=VALID_REVIEW'
  try { $output=& (Join-Path $Root 'scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1') -ProjectRoot $tempRoot -TaskId $taskId -RunId $runId -EvidenceManifestPath $manifestPath -Decision ACCEPTED -Reviewer 'Eval Reviewer' -Reason 'Deterministic evaluation of bounded pilot closure path.'; Add-Result 'PLC_VALID_HUMAN_REVIEW_DECISION' ($output -contains 'DECISION_RECORD_STATUS=COMPLETE') 'valid review' } catch { Add-Result 'PLC_VALID_HUMAN_REVIEW_DECISION' $false $_.Exception.Message }
  $reviewPath = Get-ChildItem -LiteralPath (Join-Path $tempRoot 'audit\human_reviews') -File -Filter '*.json' | Select-Object -First 1
  'EVAL_STAGE=VALID_ARCHIVE'
  try { $output=& (Join-Path $Root 'scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1') -ProjectRoot $tempRoot -TaskId $taskId -ReviewRecordPath $reviewPath.FullName; Add-Result 'PLC_VALID_ARCHIVE' ($output -contains 'ARCHIVE_STATUS=COMPLETE') 'valid archive' } catch { Add-Result 'PLC_VALID_ARCHIVE' $false $_.Exception.Message }
  'EVAL_STAGE=ACTIVE_STATE_CHECK'
  try { $output=& (Join-Path $Root 'scripts\Test-ReadOnlyPilotActiveStateV1.ps1') -ProjectRoot $tempRoot; Add-Result 'PLC_ACTIVE_STATE_CLEARED' ($output -contains 'ACTIVE_PILOT_STATE=PASS') 'active state cleared' } catch { Add-Result 'PLC_ACTIVE_STATE_CLEARED' $false $_.Exception.Message }
  # Negative fixtures must be copied to a sibling temp root, never beneath $tempRoot.
  $badRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("pwf_plc_eval_bad_" + [Guid]::NewGuid().ToString('N'))
  $tempPrefix = $tempRoot.TrimEnd('\','/') + [System.IO.Path]::DirectorySeparatorChar
  if ($badRoot.StartsWith($tempPrefix,[System.StringComparison]::OrdinalIgnoreCase)) { throw "EVAL_BAD_ROOT_INSIDE_TEMP_ROOT_FORBIDDEN=$badRoot" }
  New-Item -ItemType Directory -Path $badRoot -Force | Out-Null
  'EVAL_STAGE=NEGATIVE_FIXTURE_COPY_OUTSIDE_TEMP_ROOT'
  foreach ($item in @(Get-ChildItem -LiteralPath $tempRoot -Force)) { Copy-Item -LiteralPath $item.FullName -Destination $badRoot -Recurse -Force }
  $badTaskPath=Join-Path $badRoot "tasks\approved\$taskId.json"; if (-not (Test-Path -LiteralPath $badTaskPath)) { Copy-Item -LiteralPath (Join-Path $tempRoot "tasks\archived\$taskId.json") -Destination $badTaskPath -Force; $badTask=Get-Content $badTaskPath -Raw | ConvertFrom-Json; $badTask.status='APPROVED_FOR_READ_ONLY_RUN'; $badTask | ConvertTo-Json -Depth 10 | Set-Content $badTaskPath -Encoding UTF8 }
  @('OUTPUT_CONTRACT_START','ROLE=coordinator','OUTPUT_CONTRACT_END') | Set-Content -LiteralPath (Join-Path $badRoot "output\read_only_context_runs\$runId.canonical.txt") -Encoding UTF8
  'EVAL_STAGE=NEGATIVE_CANONICAL_REJECTION'
  try { & (Join-Path $Root 'scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1') -ProjectRoot $badRoot -TaskId $taskId -RunId $runId -EvidenceManifestPath (Join-Path $badRoot "output\evidence_manifests\EVM-$taskId.json") -Decision ACCEPTED -Reviewer 'Eval Reviewer' -Reason 'Deterministic evaluation of invalid canonical output.' | Out-Null; Add-Result 'PLC_REJECT_INVALID_CANONICAL' $false 'unexpected success' } catch { Add-Result 'PLC_REJECT_INVALID_CANONICAL' $true 'rejected' }
  'EVAL_STAGE=NEGATIVE_MANIFEST_REJECTION'
  try { $badManifest=Get-Content -LiteralPath (Join-Path $badRoot "output\evidence_manifests\EVM-$taskId.json") -Raw | ConvertFrom-Json; $badManifest.task_id='OTHER'; $badManifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $badRoot "output\evidence_manifests\EVM-$taskId.json") -Encoding UTF8; & (Join-Path $Root 'scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1') -ProjectRoot $badRoot -TaskId $taskId -RunId $runId -EvidenceManifestPath (Join-Path $badRoot "output\evidence_manifests\EVM-$taskId.json") -Decision ACCEPTED -Reviewer 'Eval Reviewer' -Reason 'Deterministic evaluation of wrong manifest task.' | Out-Null; Add-Result 'PLC_REJECT_MANIFEST_TASK_MISMATCH' $false 'unexpected success' } catch { Add-Result 'PLC_REJECT_MANIFEST_TASK_MISMATCH' $true 'rejected' }
  'EVAL_STAGE=NEGATIVE_ARCHIVE_REJECTION'
  try { & (Join-Path $Root 'scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1') -ProjectRoot $badRoot -TaskId $taskId -ReviewRecordPath (Join-Path $badRoot 'audit\missing.json') | Out-Null; Add-Result 'PLC_REJECT_ARCHIVE_WITHOUT_REVIEW' $false 'unexpected success' } catch { Add-Result 'PLC_REJECT_ARCHIVE_WITHOUT_REVIEW' $true 'rejected' }
} finally {
  foreach ($cleanupPath in @($badRoot,$tempRoot)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$cleanupPath) -and (Test-Path -LiteralPath $cleanupPath -PathType Container)) {
      Remove-Item -LiteralPath $cleanupPath -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
}
$outputDir=Join-Path $Root 'output\evals'; New-Item -ItemType Directory -Path $outputDir -Force | Out-Null; $stamp=Get-Date -Format 'yyyyMMddHHmmss'; $reportPath=Join-Path $outputDir "READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_EVAL_REPORT_$stamp.json"; $results | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
$passed=@($results|Where-Object{$_.passed}).Count; $failed=$results.Count-$passed
"EVAL_CASE_COUNT=$($results.Count)"; "EVAL_PASSED_COUNT=$passed"; "EVAL_FAILED_COUNT=$failed"; "EVAL_REPORT_PATH=$reportPath"; 'TASK_GENERATION=NONE'; 'MODEL_EXECUTION=NONE'; 'PLATFORM_MUTATION=NONE'; 'DATABASE_ACCESS=NONE'; 'GIT_WRITE=NONE'; 'DEPLOYMENT=NONE'; 'SECRETS_ACCESS=NONE'; 'MEMORY_WRITE=NONE'
if ($failed -eq 0) { 'FINAL_RESULT=PASS'; exit 0 }; 'FINAL_RESULT=FAIL'; exit 1
