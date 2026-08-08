[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$TaskId,
  [Parameter(Mandatory = $true)][string]$ReviewRecordPath
)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$source = Join-Path $Root "tasks\approved\$TaskId.json"
$reviewRoot = [System.IO.Path]::GetFullPath((Join-Path $Root 'audit\human_reviews'))
$reviewFull = [System.IO.Path]::GetFullPath($ReviewRecordPath)
$reviewPrefix = $reviewRoot.TrimEnd('\','/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $reviewFull.StartsWith($reviewPrefix,[System.StringComparison]::OrdinalIgnoreCase)) { throw "REVIEW_RECORD_OUTSIDE_AUDIT_ROOT=$reviewFull" }
foreach ($path in @($source,$reviewFull)) { if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "REQUIRED_PATH_NOT_FOUND=$path" } }
$task = Get-Content -LiteralPath $source -Raw -Encoding UTF8 | ConvertFrom-Json
$review = Get-Content -LiteralPath $reviewFull -Raw -Encoding UTF8 | ConvertFrom-Json
if ($task.status -ne 'APPROVED_FOR_READ_ONLY_RUN') { throw "TASK_NOT_ARCHIVABLE_STATUS=$($task.status)" }
if ($review.record_type -ne 'HUMAN_REVIEW_DECISION' -or $review.review_scope -ne 'READ_ONLY_PILOT_RUN_REVIEW_ONLY') { throw 'REVIEW_RECORD_TYPE_INVALID' }
if ($review.task_id -ne $TaskId) { throw "REVIEW_TASK_MISMATCH=$($review.task_id)" }
if (@('ACCEPTED','REJECTED') -notcontains [string]$review.decision) { throw "REVIEW_DECISION_INVALID=$($review.decision)" }
if ($review.verification.model_output_valid -ne $true -or $review.verification.system_owned_envelope_created -ne $true -or $review.verification.run_status -ne 'PENDING_HUMAN_REVIEW') { throw 'REVIEW_VERIFICATION_NOT_SUFFICIENT' }
if ($null -eq $review.artifacts -or $null -eq $review.artifact_hashes) { throw 'REVIEW_ARTIFACT_BINDING_MISSING' }
$expectedPairs = @(
  @{path=[string]$review.artifacts.canonical_path; expected=[string]$review.artifact_hashes.canonical_sha256; name='canonical'},
  @{path=[string]$review.artifacts.raw_path; expected=[string]$review.artifact_hashes.raw_sha256; name='raw'},
  @{path=[string]$review.artifacts.report_path; expected=[string]$review.artifact_hashes.report_sha256; name='report'},
  @{path=[string]$review.evidence_manifest_path; expected=[string]$review.artifact_hashes.evidence_manifest_sha256; name='evidence_manifest'}
)
foreach ($pair in $expectedPairs) {
  if ([string]::IsNullOrWhiteSpace($pair.path) -or [string]::IsNullOrWhiteSpace($pair.expected)) { throw "REVIEW_ARTIFACT_HASH_MISSING=$($pair.name)" }
  if (-not (Test-Path -LiteralPath $pair.path -PathType Leaf)) { throw "REVIEW_ARTIFACT_NOT_FOUND=$($pair.name)" }
  $actual = (Get-FileHash -LiteralPath $pair.path -Algorithm SHA256).Hash
  if ($actual -ne $pair.expected) { throw "REVIEW_ARTIFACT_HASH_MISMATCH=$($pair.name)" }
}
$archiveDir = Join-Path $Root 'tasks\archived'
$destination = Join-Path $archiveDir "$TaskId.json"
if (Test-Path -LiteralPath $destination) { throw "ARCHIVE_DESTINATION_ALREADY_EXISTS=$destination" }
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Root "backups\read_only_pilot_lifecycle_closure_v1_$stamp"
$backupPath = Join-Path $backupRoot "tasks\approved\$TaskId.json"
$task.status = 'ARCHIVED_AFTER_HUMAN_REVIEW'
$task | Add-Member -NotePropertyName human_review_closure -NotePropertyValue ([ordered]@{ review_id=$review.review_id; review_record_path=$reviewFull; decision=$review.decision; reviewer=$review.reviewer; closed_at_utc=[DateTime]::UtcNow.ToString('o'); closure_scope='ARCHIVE_ONLY_NO_OPERATIONAL_EFFECT' }) -Force
if ($PSCmdlet.ShouldProcess($backupPath,'Backup approved task before human-review archive')) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
  Copy-Item -LiteralPath $source -Destination $backupPath -Force
}
if ($PSCmdlet.ShouldProcess($destination,'Archive read-only pilot task after human review')) {
  New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
  $task | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $destination -Encoding UTF8
  Remove-Item -LiteralPath $source -Force
  $event = [ordered]@{ event='PILOT_ARCHIVED_AFTER_HUMAN_REVIEW'; task_id=$TaskId; review_id=$review.review_id; decision=$review.decision; archived_path=$destination; at_utc=[DateTime]::UtcNow.ToString('o') }
  $event | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $Root 'audit\events.jsonl') -Encoding UTF8
}
$archiveStatus = if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' }
"ARCHIVE_STATUS=$archiveStatus"
"TASK_ID=$TaskId"
"REVIEW_ID=$($review.review_id)"
"REVIEW_DECISION=$($review.decision)"
"ARCHIVE_DESTINATION=$destination"
"BACKUP_PATH=$backupRoot"
'TASK_FINAL_STATUS=ARCHIVED_AFTER_HUMAN_REVIEW'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
'NEXT_STEP=RUN_ACTIVE_PILOT_STATE_CHECK_ONLY'
