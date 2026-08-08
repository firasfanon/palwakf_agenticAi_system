[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)] [ValidateSet('TASK','MEMORY','LEARNING')] [string]$RecordKind,
  [Parameter(Mandatory = $true)] [string]$RecordId,
  [Parameter(Mandatory = $true)] [ValidateSet('APPROVED','REJECTED')] [string]$Decision,
  [Parameter(Mandatory = $true)] [ValidateLength(2, 120)] [string]$Approver,
  [Parameter(Mandatory = $true)] [ValidateLength(3, 500)] [string]$Reason,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$locations = @{
  TASK = @{ Pending = 'tasks/inbox'; Approved = 'tasks/approved'; Rejected = 'tasks/rejected' }
  MEMORY = @{ Pending = 'memory/pending'; Approved = 'memory/approved'; Rejected = 'memory/rejected' }
  LEARNING = @{ Pending = 'memory/pending'; Approved = 'memory/approved'; Rejected = 'memory/rejected' }
}
$set = $locations[$RecordKind]
$source = Join-Path (Join-Path $Root $set.Pending) "$RecordId.json"
if (-not (Test-Path -LiteralPath $source)) { throw "PENDING_RECORD_NOT_FOUND=$source" }
$record = Get-Content -LiteralPath $source -Raw -Encoding UTF8 | ConvertFrom-Json
if ($RecordKind -eq 'TASK' -and $record.prompt_injection_suspected -eq $true -and $Decision -eq 'APPROVED') {
  throw 'PROMPT_INJECTION_SUSPECTED_TASK_CANNOT_BE_APPROVED_IN_V1'
}
if ($RecordKind -eq 'TASK' -and $Decision -eq 'APPROVED') {
  if ($record.risk -ne 'LOW' -or $record.autonomy -ne 'L0_READ_ONLY') {
    throw 'V1_RUNNER_APPROVAL_ONLY_SUPPORTS_LOW_RISK_L0_READ_ONLY_TASKS'
  }
}
$record.status = if ($Decision -eq 'APPROVED') { 'APPROVED_FOR_READ_ONLY_RUN' } else { 'REJECTED_BY_HUMAN' }
$record | Add-Member -NotePropertyName human_approval -NotePropertyValue ([ordered]@{
  approval_id = "APR-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmss'))-$RecordId"
  record_kind = $RecordKind
  record_id = $RecordId
  decision = $Decision
  approver = $Approver
  decided_at_utc = [DateTime]::UtcNow.ToString('o')
  reason = $Reason
}) -Force
$destinationDir = Join-Path $Root $(if ($Decision -eq 'APPROVED') { $set.Approved } else { $set.Rejected })
New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
$destination = Join-Path $destinationDir "$RecordId.json"
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $destination -Encoding UTF8
Remove-Item -LiteralPath $source -Force
$auditPath = Join-Path $Root 'audit/events.jsonl'
$event = [ordered]@{ event='HUMAN_APPROVAL'; record_kind=$RecordKind; record_id=$RecordId; decision=$Decision; approver=$Approver; reason=$Reason; at_utc=[DateTime]::UtcNow.ToString('o') }
$event | ConvertTo-Json -Compress | Add-Content -LiteralPath $auditPath -Encoding UTF8
"APPROVAL_STATUS=$Decision"
"RECORD_KIND=$RecordKind"
"RECORD_DESTINATION=$destination"
'HUMAN_APPROVAL_REQUIRED=YES'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
