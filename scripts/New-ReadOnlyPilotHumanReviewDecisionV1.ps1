[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$TaskId,
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$RunId,
  [Parameter(Mandatory = $true)][string]$EvidenceManifestPath,
  [Parameter(Mandatory = $true)][ValidateSet('ACCEPTED','REJECTED')][string]$Decision,
  [Parameter(Mandatory = $true)][ValidateLength(2,120)][string]$Reviewer,
  [Parameter(Mandatory = $true)][ValidateLength(10,1000)][string]$Reason
)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$taskPath = Join-Path $Root "tasks\approved\$TaskId.json"
$runRoot = Join-Path $Root 'output\read_only_context_runs'
$manifestRoot = [System.IO.Path]::GetFullPath((Join-Path $Root 'output\evidence_manifests'))
$manifestFull = [System.IO.Path]::GetFullPath($EvidenceManifestPath)
$manifestPrefix = $manifestRoot.TrimEnd('\','/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $manifestFull.StartsWith($manifestPrefix,[System.StringComparison]::OrdinalIgnoreCase)) { throw "EVIDENCE_MANIFEST_OUTSIDE_PROJECT_ROOT=$manifestFull" }
$canonicalPath = Join-Path $runRoot "$RunId.canonical.txt"
$rawPath = Join-Path $runRoot "$RunId.raw.txt"
$reportPath = Join-Path $runRoot "$RunId.report.md"
foreach ($path in @($taskPath,$canonicalPath,$rawPath,$reportPath,$manifestFull)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "REQUIRED_ARTIFACT_NOT_FOUND=$path" }
}
$task = Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($task.status -ne 'APPROVED_FOR_READ_ONLY_RUN') { throw "TASK_NOT_REVIEWABLE_STATUS=$($task.status)" }
$manifest = Get-Content -LiteralPath $manifestFull -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.task_id -ne $TaskId) { throw "MANIFEST_TASK_MISMATCH=$($manifest.task_id)" }
if ($manifest.platform_mutation -ne 'NONE' -or $manifest.database_access -ne 'NONE' -or $manifest.git_write -ne 'NONE' -or $manifest.deployment -ne 'NONE') { throw 'MANIFEST_BOUNDARY_VIOLATION' }
$canonicalLines = @(Get-Content -LiteralPath $canonicalPath -Encoding UTF8 | ForEach-Object { $_.TrimEnd() } | Where-Object { $_.Length -gt 0 })
if ($canonicalLines.Count -ne 13) { throw "CANONICAL_LINE_COUNT_INVALID=$($canonicalLines.Count)" }
if ($canonicalLines[0] -ne 'OUTPUT_CONTRACT_START' -or $canonicalLines[12] -ne 'OUTPUT_CONTRACT_END') { throw 'CANONICAL_BOUNDARIES_INVALID' }
$body = @($canonicalLines[1..11])
if (@($body | Where-Object { $_ -notmatch '^[A-Z_]+=' }).Count -ne 0) { throw 'CANONICAL_BODY_FORMAT_INVALID' }
$report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8
$requiredReportSignals = @(
  "- Task ID: $TaskId",
  '- Run status: PENDING_HUMAN_REVIEW',
  'MODEL_OUTPUT_VALID=True',
  'MODEL_OUTPUT_RAW_LINE_COUNT=11',
  'MODEL_OUTPUT_TRAILING_LINE_COUNT=0',
  'SYSTEM_OWNED_ENVELOPE_CREATED=True',
  '- PLATFORM_MUTATION: NONE',
  '- DATABASE_ACCESS: NONE',
  '- GIT_WRITE: NONE',
  '- DEPLOYMENT: NONE',
  '- SECRETS_ACCESS: NONE',
  '- MEMORY_WRITE: NONE'
)
$missingSignals = @($requiredReportSignals | Where-Object { -not $report.Contains($_) })
if ($missingSignals.Count -gt 0) { throw "REPORT_VERIFICATION_FAILED=$([string]::Join(';',$missingSignals))" }
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
$reviewId = "HRR-$stamp-$TaskId"
$reviewDir = Join-Path $Root 'audit\human_reviews'
$reviewPath = Join-Path $reviewDir "$reviewId.json"
$hashes = [ordered]@{
  canonical_sha256 = (Get-FileHash -LiteralPath $canonicalPath -Algorithm SHA256).Hash
  raw_sha256 = (Get-FileHash -LiteralPath $rawPath -Algorithm SHA256).Hash
  report_sha256 = (Get-FileHash -LiteralPath $reportPath -Algorithm SHA256).Hash
  evidence_manifest_sha256 = (Get-FileHash -LiteralPath $manifestFull -Algorithm SHA256).Hash
}
$record = [ordered]@{
  review_id = $reviewId
  record_type = 'HUMAN_REVIEW_DECISION'
  review_scope = 'READ_ONLY_PILOT_RUN_REVIEW_ONLY'
  task_id = $TaskId
  run_id = $RunId
  decision = $Decision
  reviewer = $Reviewer
  reason = $Reason
  decided_at_utc = [DateTime]::UtcNow.ToString('o')
  task_status_at_review = $task.status
  evidence_manifest_path = $manifestFull
  artifacts = [ordered]@{
    canonical_path = $canonicalPath
    raw_path = $rawPath
    report_path = $reportPath
  }
  artifact_hashes = $hashes
  verification = [ordered]@{
    model_output_valid = $true
    model_output_raw_line_count = 11
    model_output_trailing_line_count = 0
    system_owned_envelope_created = $true
    run_status = 'PENDING_HUMAN_REVIEW'
    platform_mutation = 'NONE'
    database_access = 'NONE'
    git_write = 'NONE'
    deployment = 'NONE'
    secrets_access = 'NONE'
    memory_write = 'NONE'
  }
  non_effects = @('NO_PLATFORM_AUTHORITY','NO_DATABASE_AUTHORITY','NO_GIT_AUTHORITY','NO_DEPLOYMENT_AUTHORITY','NO_SECRETS_AUTHORITY','NO_MEMORY_PROMOTION','NO_ADDITIONAL_MODEL_RUN')
}
if ($PSCmdlet.ShouldProcess($reviewPath,'Write human review decision record')) {
  New-Item -ItemType Directory -Path $reviewDir -Force | Out-Null
  $record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $reviewPath -Encoding UTF8
  $event = [ordered]@{ event='HUMAN_REVIEW_DECISION'; review_id=$reviewId; task_id=$TaskId; run_id=$RunId; decision=$Decision; reviewer=$Reviewer; reason=$Reason; at_utc=[DateTime]::UtcNow.ToString('o') }
  $event | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $Root 'audit\events.jsonl') -Encoding UTF8
}
$decisionStatus = if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' }
"DECISION_RECORD_STATUS=$decisionStatus"
"REVIEW_ID=$reviewId"
"REVIEW_RECORD_PATH=$reviewPath"
"TASK_ID=$TaskId"
"RUN_ID=$RunId"
"REVIEW_DECISION=$Decision"
'RUN_VALIDATED=True'
'HUMAN_REVIEW_REQUIRED=YES'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
'NEXT_STEP=ARCHIVE_TASK_ONLY_WITH_VALID_REVIEW_RECORD'
