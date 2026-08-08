[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @(
  'agents/registry/AGENT_SKILL_ASSIGNMENTS_V1.json',
  'skills/registry/SKILL_REGISTRY_RUNTIME_V1.json',
  'task_contracts/TASK_INTAKE_SCHEMA_V1.json',
  'task_contracts/TASK_RUN_SCHEMA_V1.json',
  'task_contracts/MEMORY_RECORD_SCHEMA_V1.json',
  'task_contracts/APPROVAL_RECORD_SCHEMA_V1.json',
  'governance/operational_activation/PALWAKF_OPERATIONAL_ACTIVATION_POLICY_V1.md',
  'governance/operational_activation/TOOL_GATEWAY_POLICY_V1.md',
  'governance/operational_activation/HUMAN_APPROVAL_GATE_V1.md',
  'governance/operational_activation/PROMPT_INJECTION_RESPONSE_V1.md',
  'scripts/New-LocalAgentTaskV1.ps1',
  'scripts/Set-HumanApprovalV1.ps1',
  'scripts/Invoke-ReadOnlyToolGatewayV1.ps1',
  'scripts/Invoke-ReadOnlyTaskRunnerV1.ps1',
  'scripts/Invoke-AgentEvalsV1.ps1',
  'tasks/inbox', 'tasks/approved', 'tasks/rejected',
  'memory/pending', 'memory/approved', 'memory/rejected',
  'output/read_only_runs', 'audit', 'reference_sources/approved'
)
$missing = @()
foreach ($relative in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) { $missing += $relative }
}

$registryPath = Join-Path $Root 'agents/registry/AGENT_SKILL_ASSIGNMENTS_V1.json'
$skillsPath = Join-Path $Root 'skills/registry/SKILL_REGISTRY_RUNTIME_V1.json'
$registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skills = Get-Content -LiteralPath $skillsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$skillIds = @($skills.skills | ForEach-Object { $_.skill_id })
$unknownAssignments = @()
foreach ($agent in $registry.agents) {
  foreach ($skill in $agent.allowed_skills) {
    if ($skillIds -notcontains $skill) { $unknownAssignments += "$($agent.agent_id):$skill" }
  }
}
$runtimeAgents = @($registry.agents | Where-Object { $_.runtime_enabled -eq $true })
$expectedAgents = @('coordinator','sovereignty_reviewer')
$runtimeNames = @($runtimeAgents | ForEach-Object { $_.agent_id })
$invalidRuntime = @($runtimeNames | Where-Object { $expectedAgents -notcontains $_ })

"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"SKILL_RUNTIME_COUNT=$($skills.skills.Count)"
"SKILL_ASSIGNMENT_COUNT=$(($registry.agents | ForEach-Object { $_.allowed_skills.Count } | Measure-Object -Sum).Sum)"
"RUNTIME_ENABLED_AGENT_COUNT=$($runtimeAgents.Count)"
"UNKNOWN_SKILL_ASSIGNMENT_COUNT=$($unknownAssignments.Count)"
"INVALID_RUNTIME_AGENT_COUNT=$($invalidRuntime.Count)"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if ($missing.Count -eq 0 -and $unknownAssignments.Count -eq 0 -and $invalidRuntime.Count -eq 0 -and $runtimeAgents.Count -eq 2) {
  'FINAL_RESULT=PASS'
  exit 0
}
'MISSING_OR_INVALID_ITEMS='
$missing + $unknownAssignments + $invalidRuntime | ForEach-Object { $_ }
'FINAL_RESULT=FAIL'
exit 1
