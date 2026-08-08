[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$TaskId,

  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),

  [int]$MaxCharsPerReference = 6000
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$taskPath = Join-Path $Root "tasks\approved\$TaskId.json"

if (-not (Test-Path -LiteralPath $taskPath)) {
  throw "APPROVED_TASK_NOT_FOUND=$taskPath"
}

$task = Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($task.status -ne 'APPROVED_FOR_READ_ONLY_RUN') {
  throw "TASK_NOT_RUNNABLE_STATUS=$($task.status)"
}

if ($task.risk -ne 'LOW' -or $task.autonomy -ne 'L0_READ_ONLY') {
  throw 'TASK_OUTSIDE_READ_ONLY_BOUNDARY'
}

$modulePath = Join-Path $Root 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'
Import-Module $modulePath -Force

if ($null -eq (Get-Command -Name 'New-ReferenceEvidenceManifest' -ErrorAction SilentlyContinue)) {
  throw 'EVIDENCE_MANIFEST_FUNCTION_NOT_AVAILABLE'
}

$manifest = New-ReferenceEvidenceManifest `
  -ProjectRoot $Root `
  -Task $task `
  -MaxCharsPerReference $MaxCharsPerReference

$outputDirectory = Join-Path $Root 'output\evidence_manifests'
$auditDirectory = Join-Path $Root 'audit'

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $auditDirectory -Force | Out-Null

$outputPath = Join-Path $outputDirectory "$($manifest.manifest_id).json"

$manifest |
  ConvertTo-Json -Depth 12 |
  Set-Content -LiteralPath $outputPath -Encoding UTF8

$event = [ordered]@{
  event = 'READ_ONLY_EVIDENCE_MANIFEST_CREATED'
  task_id = $TaskId
  manifest_id = $manifest.manifest_id
  manifest_path = $outputPath
  at_utc = [DateTime]::UtcNow.ToString('o')
  platform_mutation = 'NONE'
  database_access = 'NONE'
  git_write = 'NONE'
  deployment = 'NONE'
}

$event |
  ConvertTo-Json -Compress |
  Add-Content -LiteralPath (Join-Path $auditDirectory 'events.jsonl') -Encoding UTF8

$securityFlagCount = (
  $manifest.evidence_items |
    ForEach-Object { @($_.security_flags).Count } |
    Measure-Object -Sum
).Sum

"TASK_ID=$TaskId"
"EVIDENCE_MANIFEST_ID=$($manifest.manifest_id)"
"EVIDENCE_ITEM_COUNT=$(@($manifest.evidence_items).Count)"
"SECURITY_FLAG_COUNT=$securityFlagCount"
"EVIDENCE_MANIFEST_PATH=$outputPath"
'TOOL_MODE=READ_ONLY_EVIDENCE_GATEWAY'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
