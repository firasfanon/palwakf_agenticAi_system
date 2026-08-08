[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$requiredBaselineFiles = @(
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1'
)

$missingFiles = @()

foreach ($relative in $requiredBaselineFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missingFiles += $relative
  }
}

$registryFailures = @()

if ($missingFiles.Count -eq 0) {
  $registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

  foreach ($agentId in @('knowledge_researcher', 'documentation_handoff')) {
    $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

    if ($matches.Count -ne 1) {
      $registryFailures += "AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
      continue
    }

    $agent = $matches[0]

    if (($agent.runtime_enabled -ne $true) -or ($agent.runtime_mode -ne 'read_only_report_only')) {
      $registryFailures += "RUNTIME_STATE_INVALID:${agentId}"
    }

    if (@($agent.allowed_autonomy) -notcontains 'L0_READ_ONLY') {
      $registryFailures += "L0_READ_ONLY_MISSING:${agentId}"
    }

    if (@($agent.allowed_skills) -notcontains 'task_triage') {
      $registryFailures += "TASK_TRIAGE_MISSING:${agentId}"
    }

    if (@($agent.allowed_skills) -notcontains 'evidence_assessment') {
      $registryFailures += "EVIDENCE_ASSESSMENT_MISSING:${agentId}"
    }
  }

  $knowledgeResearcher = @($registry.agents | Where-Object { $_.agent_id -eq 'knowledge_researcher' })[0]
  $documentationHandoff = @($registry.agents | Where-Object { $_.agent_id -eq 'documentation_handoff' })[0]

  if (($null -ne $knowledgeResearcher) -and (@($knowledgeResearcher.allowed_skills) -notcontains 'knowledge_source_review')) {
    $registryFailures += 'KNOWLEDGE_SOURCE_REVIEW_SKILL_MISSING'
  }

  if (($null -ne $documentationHandoff) -and (@($documentationHandoff.allowed_skills) -contains 'documentation_handoff')) {
    $registryFailures += 'DOCUMENTATION_HANDOFF_SKILL_ALREADY_PRESENT'
  }
}

"REQUIRED_BASELINE_FILE_COUNT=$($requiredBaselineFiles.Count)"
"MISSING_BASELINE_FILE_COUNT=$($missingFiles.Count)"
"MISSING_BASELINE_FILES=$([string]::Join(';', $missingFiles))"
"REGISTRY_PREFLIGHT_FAILURE_COUNT=$($registryFailures.Count)"
"REGISTRY_PREFLIGHT_FAILURES=$([string]::Join(';', $registryFailures))"
'BASELINE_RECHECK_REQUIRED=YES'
'REGISTRY_MUTATION_ON_APPLY=DOCUMENTATION_HANDOFF_SKILL_ONLY'
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'

if (($missingFiles.Count -eq 0) -and ($registryFailures.Count -eq 0)) {
  'PREFLIGHT_RESULT=PASS'
  exit 0
}

'PREFLIGHT_RESULT=FAIL'
exit 1
