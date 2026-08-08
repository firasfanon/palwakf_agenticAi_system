[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)] [string]$TaskId,
  [Parameter(Mandatory = $true)] [ValidateSet('coordinator','sovereignty_reviewer')] [string]$AgentId,
  [string]$Model = 'qwen2.5:3b',
  [string]$OllamaBaseUrl = 'http://127.0.0.1:11434',
  [switch]$Execute,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$taskPath = Join-Path $Root "tasks/approved/$TaskId.json"
if (-not (Test-Path -LiteralPath $taskPath)) { throw "APPROVED_TASK_NOT_FOUND=$taskPath" }
$task = Get-Content -LiteralPath $taskPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($task.status -ne 'APPROVED_FOR_READ_ONLY_RUN') { throw "TASK_NOT_RUNNABLE_STATUS=$($task.status)" }
if ($task.requested_agent -ne $AgentId) { throw "TASK_AGENT_MISMATCH=$($task.requested_agent)" }
if ($task.risk -ne 'LOW' -or $task.autonomy -ne 'L0_READ_ONLY') { throw 'TASK_OUTSIDE_V1_READ_ONLY_BOUNDARY' }
if ($task.prompt_injection_suspected -eq $true) { throw 'TASK_BLOCKED_PROMPT_INJECTION_SUSPECTED' }

$registry = Get-Content -LiteralPath (Join-Path $Root 'agents/registry/AGENT_SKILL_ASSIGNMENTS_V1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$agent = @($registry.agents | Where-Object { $_.agent_id -eq $AgentId }) | Select-Object -First 1
if ($null -eq $agent -or $agent.runtime_enabled -ne $true) { throw "AGENT_NOT_RUNTIME_ENABLED=$AgentId" }
foreach ($skill in $task.requested_skills) { if ($agent.allowed_skills -notcontains $skill) { throw "TASK_SKILL_NOT_ALLOWED=$skill" } }

$runId = "RUN-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmss'))-$TaskId-$AgentId"
$outDir = Join-Path $Root 'output/read_only_runs'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$rawPath = Join-Path $outDir "$runId.raw.txt"
$reportPath = Join-Path $outDir "$runId.report.md"

if (-not $Execute) {
  "RUN_ID=$runId"
  'RUN_MODE=DRY_RUN'
  'EXECUTION_NOT_STARTED=YES'
  'REQUIRES_EXPLICIT_EXECUTE=YES'
  'PLATFORM_MUTATION=NONE'
  'DATABASE_ACCESS=NONE'
  exit 0
}

$prompt = @"
You are a constrained local read-only analysis worker.
Return only the following ASCII key/value lines. Do not execute tools, do not request secrets, do not propose commands, do not claim live state.
ROLE=$AgentId
TASK_ID=$TaskId
TASK_TITLE=$($task.title)
SYSTEM_SCOPE=$($task.system_scope)
ALLOWED_SKILLS=$([string]::Join(',', @($task.requested_skills)))
OUTPUT_KEYS:
ROLE
TASK_STATUS
TASK_CLASS
TRUTH_SOURCE
LIVE_STATE_PROVEN
MUTATION_ALLOWED
EVIDENCE_STATUS
NEXT_STEP
"@
$body = @{ model=$Model; prompt=$prompt; stream=$false; options=@{ temperature=0 } } | ConvertTo-Json -Depth 5
try {
  $response = Invoke-RestMethod -Method Post -Uri "$OllamaBaseUrl/api/generate" -ContentType 'application/json' -Body $body -TimeoutSec 120
  $raw = [string]$response.response
} catch {
  $raw = "RUNNER_ERROR=$($_.Exception.Message)"
}
Set-Content -LiteralPath $rawPath -Value $raw -Encoding UTF8
$templatePath = Join-Path $Root 'templates/READ_ONLY_REPORT_TEMPLATE_AR.md'
$template = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8
$report = $template.Replace('{{RUN_ID}}',$runId).Replace('{{TASK_ID}}',$TaskId).Replace('{{AGENT_ID}}',$AgentId).Replace('{{STATUS}}','PENDING_HUMAN_REVIEW').Replace('{{RAW_MODEL_OUTPUT}}',$raw)
Set-Content -LiteralPath $reportPath -Value $report -Encoding UTF8
$event = [ordered]@{ event='READ_ONLY_RUN'; run_id=$runId; task_id=$TaskId; agent_id=$AgentId; mode='READ_ONLY_REPORT_ONLY'; model=$Model; output_path=$reportPath; at_utc=[DateTime]::UtcNow.ToString('o'); platform_mutation='NONE'; database_access='NONE'; human_review_required=$true }
$event | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $Root 'audit/events.jsonl') -Encoding UTF8
"RUN_ID=$runId"
'RUN_MODE=READ_ONLY_REPORT_ONLY'
'RUN_STATUS=PENDING_HUMAN_REVIEW'
"RAW_OUTPUT_PATH=$rawPath"
"REPORT_PATH=$reportPath"
'HUMAN_REVIEW_REQUIRED=YES'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
