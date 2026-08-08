[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$requiredFiles = @(
  'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json',
  'agents\charters\read_only_analysis_pack_01\COORDINATOR_READ_ONLY_ANALYSIS_PACK_01.md',
  'agents\charters\read_only_analysis_pack_01\SOVEREIGNTY_REVIEWER_READ_ONLY_ANALYSIS_PACK_01.md',
  'agents\charters\read_only_analysis_pack_01\KNOWLEDGE_RESEARCHER_READ_ONLY_ANALYSIS_PACK_01.md',
  'agents\charters\read_only_analysis_pack_01\DOCUMENTATION_HANDOFF_READ_ONLY_ANALYSIS_PACK_01.md',
  'agents\output_profiles\read_only_analysis_pack_01\coordinator.json',
  'agents\output_profiles\read_only_analysis_pack_01\sovereignty_reviewer.json',
  'agents\output_profiles\read_only_analysis_pack_01\knowledge_researcher.json',
  'agents\output_profiles\read_only_analysis_pack_01\documentation_handoff.json',
  'tasks\templates\read_only_analysis_pack_01\PACK01_COORDINATOR_ROUTING_PILOT_001.json',
  'tasks\templates\read_only_analysis_pack_01\PACK01_SOVEREIGNTY_REVIEW_PILOT_001.json',
  'tasks\templates\read_only_analysis_pack_01\PACK01_KNOWLEDGE_RESEARCH_PILOT_001.json',
  'tasks\templates\read_only_analysis_pack_01\PACK01_DOCUMENTATION_HANDOFF_PILOT_001.json',
  'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1'
)

$missing = @()

foreach ($relative in $requiredFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missing += $relative
  }
}

$agentFailures = @()

if ($missing.Count -eq 0) {
  $registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

  foreach ($agentId in @(
    'coordinator',
    'sovereignty_reviewer',
    'knowledge_researcher',
    'documentation_handoff'
  )) {
    $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

    if ($matches.Count -ne 1) {
      $agentFailures += "AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
      continue
    }

    $agent = $matches[0]

    if ($agent.runtime_enabled -ne $true) {
      $agentFailures += "RUNTIME_NOT_ENABLED:$agentId"
    }

    if ($agent.runtime_mode -ne 'read_only_report_only') {
      $agentFailures += "RUNTIME_MODE_INVALID:${agentId}:$($agent.runtime_mode)"
    }

    if (@($agent.allowed_skills) -notcontains 'task_triage') {
      $agentFailures += "TASK_TRIAGE_NOT_ALLOWED:$agentId"
    }

    if (@($agent.allowed_skills) -notcontains 'evidence_assessment') {
      $agentFailures += "EVIDENCE_ASSESSMENT_NOT_ALLOWED:$agentId"
    }

    if (@($agent.allowed_autonomy) -notcontains 'L0_READ_ONLY') {
      $agentFailures += "L0_READ_ONLY_NOT_ALLOWED:$agentId"
    }

    if ($agent.human_review_required -ne $true) {
      $agentFailures += "HUMAN_REVIEW_NOT_REQUIRED:$agentId"
    }
  }
}


$unsafeInterpolationFailures = @()
$scriptFiles = @(
  Get-ChildItem -LiteralPath (Join-Path $Root 'scripts') -Filter '*.ps1' -File
)

foreach ($scriptFile in $scriptFiles) {
  $scriptText = Get-Content -LiteralPath $scriptFile.FullName -Raw -Encoding UTF8

  foreach ($match in [regex]::Matches($scriptText, '\$[A-Za-z_][A-Za-z0-9_]*:')) {
    $unsafeInterpolationFailures += "$($scriptFile.Name):$($match.Value)"
  }
}

"REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$([string]::Join(';', $missing))"
"PACK_AGENT_FAILURE_COUNT=$($agentFailures.Count)"
"PACK_AGENT_FAILURES=$([string]::Join(';', $agentFailures))"
"UNSAFE_VARIABLE_COLON_INTERPOLATION_COUNT=$($unsafeInterpolationFailures.Count)"
"UNSAFE_VARIABLE_COLON_INTERPOLATIONS=$([string]::Join(';', $unsafeInterpolationFailures))"
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'

if (($missing.Count -eq 0) -and ($agentFailures.Count -eq 0) -and ($unsafeInterpolationFailures.Count -eq 0)) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
