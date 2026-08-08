[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$activeStatuses = @('APPROVED_FOR_READ_ONLY_RUN','RUNNING')
$active = @()
foreach ($relative in @('tasks\inbox','tasks\approved','tasks\archived')) {
  $directory = Join-Path $Root $relative
  if (-not (Test-Path -LiteralPath $directory -PathType Container)) { continue }
  foreach ($file in @(Get-ChildItem -LiteralPath $directory -File -Filter '*.json')) {
    try { $task = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch { throw "TASK_JSON_PARSE_FAILED=$($file.FullName)" }
    if ($activeStatuses -contains [string]$task.status) { $active += "$($task.task_id)|$($task.status)|$($file.FullName)" }
  }
}
"ACTIVE_TASK_COUNT=$($active.Count)"; "ACTIVE_TASKS=$([string]::Join(';',$active))"; 'MODEL_EXECUTION=NONE'; 'PLATFORM_MUTATION=NONE'; 'DATABASE_ACCESS=NONE'; 'GIT_WRITE=NONE'; 'DEPLOYMENT=NONE'; 'SECRETS_ACCESS=NONE'; 'MEMORY_WRITE=NONE'
if ($active.Count -eq 0) { 'ACTIVE_PILOT_STATE=PASS'; exit 0 }
'ACTIVE_PILOT_STATE=FAIL'; exit 1
