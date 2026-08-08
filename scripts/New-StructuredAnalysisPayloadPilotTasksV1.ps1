[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [ValidateSet('knowledge_researcher', 'documentation_handoff', 'all')][string]$AgentId = 'all'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$templateRoot = Join-Path $Root 'tasks\templates\structured_analysis_payload_foundation'
$inboxRoot = Join-Path $Root 'tasks\inbox'

if (-not (Test-Path -LiteralPath $templateRoot)) {
  throw "TEMPLATE_ROOT_NOT_FOUND=$templateRoot"
}

$templates = @(
  @{ agent_id = 'knowledge_researcher'; file = 'SAPF_KNOWLEDGE_RESEARCH_PILOT_001.json' },
  @{ agent_id = 'documentation_handoff'; file = 'SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json' }
)

if ($AgentId -ne 'all') {
  $templates = @($templates | Where-Object { $_.agent_id -eq $AgentId })
}

$created = @()

foreach ($template in $templates) {
  $sourcePath = Join-Path $templateRoot $template.file
  $task = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8 | ConvertFrom-Json

  if (($task.status -ne 'PENDING_HUMAN_APPROVAL') -or
      ($task.risk -ne 'LOW') -or
      ($task.autonomy -ne 'L0_READ_ONLY') -or
      ($task.human_approval_required -ne $true)) {
    throw "TEMPLATE_STATE_INVALID=$($template.file)"
  }

  $destinationPath = Join-Path $inboxRoot $template.file

  if (Test-Path -LiteralPath $destinationPath) {
    throw "INBOX_TASK_ALREADY_EXISTS=$destinationPath"
  }

  if ($PSCmdlet.ShouldProcess($destinationPath, "Create pending human-approval pilot task for $($template.agent_id)")) {
    New-Item -ItemType Directory -Path $inboxRoot -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
  }

  $created += $destinationPath
}

"TASK_GENERATION_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"GENERATED_OR_PLANNED_TASK_COUNT=$($created.Count)"
"GENERATED_OR_PLANNED_TASK_PATHS=$([string]::Join(';', $created))"
'GENERATED_TASK_STATUS=PENDING_HUMAN_APPROVAL'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
'HUMAN_REVIEW_REQUIRED=YES'
