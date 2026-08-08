[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$templateRoot = Join-Path $Root 'tasks\templates\read_only_analysis_pack_01'
$profileRoot = Join-Path $Root 'agents\output_profiles\read_only_analysis_pack_01'

if (-not (Test-Path -LiteralPath $templateRoot)) {
  throw "TEMPLATE_ROOT_NOT_FOUND=$templateRoot"
}

if (-not (Test-Path -LiteralPath $profileRoot)) {
  throw "PROFILE_ROOT_NOT_FOUND=$profileRoot"
}

$cases = @(
  @{ agent_id = 'coordinator'; task_file = 'PACK01_COORDINATOR_ROUTING_PILOT_001.json'; profile_file = 'coordinator.json' },
  @{ agent_id = 'sovereignty_reviewer'; task_file = 'PACK01_SOVEREIGNTY_REVIEW_PILOT_001.json'; profile_file = 'sovereignty_reviewer.json' },
  @{ agent_id = 'knowledge_researcher'; task_file = 'PACK01_KNOWLEDGE_RESEARCH_PILOT_001.json'; profile_file = 'knowledge_researcher.json' },
  @{ agent_id = 'documentation_handoff'; task_file = 'PACK01_DOCUMENTATION_HANDOFF_PILOT_001.json'; profile_file = 'documentation_handoff.json' }
)

$results = @()
$taskIds = @()

foreach ($case in $cases) {
  $task = Get-Content -LiteralPath (Join-Path $templateRoot $case.task_file) -Raw -Encoding UTF8 | ConvertFrom-Json
  $profile = Get-Content -LiteralPath (Join-Path $profileRoot $case.profile_file) -Raw -Encoding UTF8 | ConvertFrom-Json

  $passed = (
    $task.requested_agent -eq $case.agent_id -and
    $task.status -eq 'PENDING_HUMAN_APPROVAL' -and
    $task.risk -eq 'LOW' -and
    $task.autonomy -eq 'L0_READ_ONLY' -and
    @($task.requested_skills) -contains 'task_triage' -and
    @($task.requested_skills) -contains 'evidence_assessment' -and
    @($task.allowed_reference_paths).Count -eq 1 -and
    $task.allowed_reference_paths[0] -eq 'reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md' -and
    $task.prompt_injection_suspected -eq $false -and
    $task.human_approval_required -eq $true -and
    $task.platform_mutation -eq 'NONE' -and
    $task.database_access -eq 'NONE' -and
    $task.git_write -eq 'NONE' -and
    $task.deployment -eq 'NONE' -and
    $task.secrets_access -eq 'NONE' -and
    $task.memory_write -eq 'NONE' -and
    $profile.agent_id -eq $case.agent_id -and
    $profile.runtime_mode -eq 'read_only_report_only' -and
    $profile.autonomy -eq 'L0_READ_ONLY' -and
    $profile.requires_human_review -eq $true -and
    $profile.model_output_contract -eq 'MODEL_OUTPUT_CONTRACT_V3_SYSTEM_OWNED_ENVELOPE'
  )

  $taskIds += [string]$task.task_id
  $results += [PSCustomObject]@{
    case_id = "PACK01_TEMPLATE_PROFILE_$($case.agent_id)"
    passed = $passed
  }
}

$results += [PSCustomObject]@{
  case_id = 'PACK01_TASK_IDS_UNIQUE'
  passed = (@($taskIds | Select-Object -Unique).Count -eq $taskIds.Count)
}

$outputDirectory = Join-Path $Root 'output\evals'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$reportPath = Join-Path $outputDirectory "READ_ONLY_ANALYSIS_PACK_01_V1_2_EVAL_REPORT_$stamp.json"

$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8

$passedCount = @($results | Where-Object { $_.passed }).Count
$failedCount = $results.Count - $passedCount

"EVAL_CASE_COUNT=$($results.Count)"
"EVAL_PASSED_COUNT=$passedCount"
"EVAL_FAILED_COUNT=$failedCount"
"EVAL_REPORT_PATH=$reportPath"
'TASK_GENERATION=NONE'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'

if ($failedCount -eq 0) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
