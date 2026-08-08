[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$templateRoot = Join-Path $Root 'tasks\templates\read_only_analysis_pack_01'
$inboxRoot = Join-Path $Root 'tasks\inbox'
$approvedRoot = Join-Path $Root 'tasks\approved'

if (-not (Test-Path -LiteralPath $templateRoot)) {
  throw "TEMPLATE_ROOT_NOT_FOUND=$templateRoot"
}

$templateFiles = @(Get-ChildItem -LiteralPath $templateRoot -Filter '*.json' -File | Sort-Object Name)

if ($templateFiles.Count -ne 4) {
  throw "PACK01_TEMPLATE_COUNT_INVALID=$($templateFiles.Count)"
}

$preparedTasks = @()

foreach ($templateFile in $templateFiles) {
  $task = Get-Content -LiteralPath $templateFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
  $taskId = [string]$task.task_id

  if ([string]::IsNullOrWhiteSpace($taskId)) {
    throw "TEMPLATE_TASK_ID_MISSING=$($templateFile.Name)"
  }

  foreach ($candidate in @(
    (Join-Path $inboxRoot "$taskId.json"),
    (Join-Path $approvedRoot "$taskId.json")
  )) {
    if (Test-Path -LiteralPath $candidate) {
      throw "TASK_ALREADY_EXISTS=$candidate"
    }
  }

  $task | Add-Member -NotePropertyName 'created_at_utc' -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
  $task | Add-Member -NotePropertyName 'created_by' -NotePropertyValue 'LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_2_TASK_GENERATOR'

  $preparedTasks += [PSCustomObject]@{
    task_id = $taskId
    destination = (Join-Path $inboxRoot "$taskId.json")
    task = $task
  }
}

if ($PSCmdlet.ShouldProcess($inboxRoot, 'Create Pack 01 V1.2 pending-human-approval tasks')) {
  New-Item -ItemType Directory -Path $inboxRoot -Force | Out-Null

  foreach ($prepared in $preparedTasks) {
    $prepared.task | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $prepared.destination -Encoding UTF8
  }
}

"TASK_CREATION_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"TASK_TEMPLATE_COUNT=$($templateFiles.Count)"
"TASK_CREATED_OR_PLANNED_COUNT=$($preparedTasks.Count)"
"TASK_IDS=$([string]::Join(',', @($preparedTasks | ForEach-Object { $_.task_id })))"
'TASK_STATUS=PENDING_HUMAN_APPROVAL'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
