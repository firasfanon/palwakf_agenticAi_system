[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Z0-9_-]+$')][string]$TaskId,
  [Parameter(Mandatory=$true)][ValidateLength(5,180)][string]$Title,
  [Parameter(Mandatory=$true)][ValidateLength(10,4000)][string]$Description,
  [Parameter(Mandatory=$true)][string]$SystemScope,
  [Parameter(Mandatory=$true)][ValidateSet('coordinator','sovereignty_reviewer')][string]$RequestedAgent,
  [Parameter(Mandatory=$true)][string[]]$RequestedSkills,
  [Parameter(Mandatory=$true)][string[]]$AllowedReferencePaths,
  [string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference='Stop'
$Root=[System.IO.Path]::GetFullPath($ProjectRoot)
Import-Module (Join-Path $Root 'runtime/ReadOnlyRuntimeContextEvidenceV1.psm1') -Force
if (@($AllowedReferencePaths).Count -gt 3) { throw 'MAX_REFERENCE_FILE_COUNT_EXCEEDED' }
foreach ($relative in $AllowedReferencePaths) {
  $safe=ConvertTo-SafeRelativeReferencePath -RelativePath $relative
  $full=Join-Path $Root $safe
  if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "APPROVED_REFERENCE_NOT_FOUND=$safe" }
}
$registry=Get-Content -LiteralPath (Join-Path $Root 'agents/registry/AGENT_SKILL_ASSIGNMENTS_V1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$agent=@($registry.agents | Where-Object { $_.agent_id -eq $RequestedAgent }) | Select-Object -First 1
if ($null -eq $agent -or $agent.runtime_enabled -ne $true) { throw "AGENT_NOT_RUNTIME_ENABLED=$RequestedAgent" }
foreach ($skill in $RequestedSkills) { if ($agent.allowed_skills -notcontains $skill) { throw "SKILL_NOT_ALLOWED_FOR_AGENT=${RequestedAgent}:$skill" } }
$flags=Get-ReferenceSecurityFlags -Text $Description
$task=[ordered]@{
  task_id=$TaskId; title=$Title; description=$Description; system_scope=$SystemScope;
  risk='LOW'; autonomy='L0_READ_ONLY'; status='DRAFT'; requested_agent=$RequestedAgent;
  requested_skills=@($RequestedSkills); evidence_required=@('task_definition','approved_reference_manifest','human_approval');
  allowed_reference_paths=@($AllowedReferencePaths); human_approval_required=$true;
  prompt_injection_suspected=($flags.Count -gt 0); task_security_flags=@($flags);
  platform_mutation='NONE'; database_access='NONE'; git_write='NONE'; deployment='NONE';
  created_at_utc=[DateTime]::UtcNow.ToString('o')
}
if ($task.prompt_injection_suspected) { $task.status='BLOCKED_SECURITY_REVIEW' }
$outDir=Join-Path $Root 'tasks/inbox'; New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$outPath=Join-Path $outDir "$TaskId.json"
if (Test-Path -LiteralPath $outPath) { throw "TASK_ALREADY_EXISTS=$outPath" }
$task | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
"TASK_CREATED=$outPath"
"TASK_STATUS=$($task.status)"
"TASK_REFERENCE_PATH_COUNT=$(@($AllowedReferencePaths).Count)"
"TASK_SECURITY_FLAG_COUNT=$($flags.Count)"
'HUMAN_APPROVAL_REQUIRED=YES'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
