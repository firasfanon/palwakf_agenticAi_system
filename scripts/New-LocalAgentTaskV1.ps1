[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)] [ValidatePattern('^[A-Z0-9_-]+$')] [string]$TaskId,
  [Parameter(Mandatory = $true)] [ValidateLength(5, 180)] [string]$Title,
  [Parameter(Mandatory = $true)] [string]$SystemScope,
  [Parameter(Mandatory = $true)] [ValidateSet('LOW','MEDIUM','HIGH','CRITICAL')] [string]$Risk,
  [Parameter(Mandatory = $true)] [ValidateSet('L0_READ_ONLY','L1_PLAN_ONLY','L2_PATCH_ALLOWED','L3_BATCH_ALLOWED','L4_REVIEW_REQUIRED','L5_STAGING_DEPLOY','L6_PRODUCTION_RESTRICTED')] [string]$Autonomy,
  [Parameter(Mandatory = $true)] [ValidateSet('coordinator','sovereignty_reviewer')] [string]$RequestedAgent,
  [string[]]$RequestedSkills = @(),
  [string[]]$AllowedReferencePaths = @(),
  [string]$Description = '',
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$registry = Get-Content -LiteralPath (Join-Path $Root 'agents/registry/AGENT_SKILL_ASSIGNMENTS_V1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$agent = @($registry.agents | Where-Object { $_.agent_id -eq $RequestedAgent }) | Select-Object -First 1
if ($null -eq $agent) { throw "AGENT_NOT_FOUND=$RequestedAgent" }
foreach ($skill in $RequestedSkills) {
  if ($agent.allowed_skills -notcontains $skill) { throw "SKILL_NOT_ALLOWED_FOR_AGENT=$($RequestedAgent):$skill" }
}
$injectionPattern = '(?i)(ignore\s+(all|previous)|reveal\s+(secret|token|password)|bypass\s+(review|policy)|force\s+publish|deploy\s+now|delete\s+(all|table|data)|run\s+sql)'
$injectionSuspected = $Description -match $injectionPattern
$status = if ($injectionSuspected) { 'BLOCKED_SECURITY_REVIEW' } else { 'DRAFT' }
$task = [ordered]@{
  task_id = $TaskId
  title = $Title
  system_scope = $SystemScope
  risk = $Risk
  autonomy = $Autonomy
  status = $status
  requested_agent = $RequestedAgent
  requested_skills = @($RequestedSkills)
  evidence_required = @('task_definition','approved_reference_paths','human_approval')
  allowed_reference_paths = @($AllowedReferencePaths)
  description = $Description
  prompt_injection_suspected = [bool]$injectionSuspected
  human_approval_required = $true
  platform_mutation = 'NONE'
  database_access = 'NONE'
  git_write = 'NONE'
  deployment = 'NONE'
  created_at_utc = [DateTime]::UtcNow.ToString('o')
}
$outDir = Join-Path $Root 'tasks/inbox'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$outPath = Join-Path $outDir "$TaskId.json"
if (Test-Path -LiteralPath $outPath) { throw "TASK_ALREADY_EXISTS=$outPath" }
$task | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding UTF8
"TASK_CREATED=$outPath"
"TASK_STATUS=$status"
"PROMPT_INJECTION_SUSPECTED=$injectionSuspected"
'HUMAN_APPROVAL_REQUIRED=YES'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
