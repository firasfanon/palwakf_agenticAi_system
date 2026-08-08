[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$requiredFiles = @(
  'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json',
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md'
)

$missingFiles = @()

foreach ($relative in $requiredFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missingFiles += $relative
  }
}

$registryFailures = @()
$documentationState = 'NOT_CHECKED'
$knowledgeResearcherState = 'NOT_CHECKED'

if ($missingFiles.Count -eq 0) {
  $registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

  if ($registry.registry_version -ne '1.0') {
    $registryFailures += "REGISTRY_VERSION_INVALID:$($registry.registry_version)"
  }

  if ($registry.execution_default -ne 'disabled') {
    $registryFailures += "EXECUTION_DEFAULT_INVALID:$($registry.execution_default)"
  }

  if ($null -eq $registry.agents) {
    $registryFailures += 'REGISTRY_AGENTS_ARRAY_MISSING'
  }
  else {
    foreach ($agentId in @('coordinator', 'sovereignty_reviewer', 'knowledge_researcher')) {
      $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

      if ($matches.Count -ne 1) {
        $registryFailures += "REQUIRED_AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
      }
    }

    $documentationMatches = @($registry.agents | Where-Object { $_.agent_id -eq 'documentation_handoff' })

    if ($documentationMatches.Count -eq 0) {
      $documentationState = 'ABSENT_BOOTSTRAP_REQUIRED'
    }
    elseif ($documentationMatches.Count -eq 1) {
      $documentationState = 'ALREADY_PRESENT_STOP_NO_REAPPLY'
      $registryFailures += 'DOCUMENTATION_HANDOFF_ALREADY_PRESENT'
    }
    else {
      $documentationState = "DUPLICATE_COUNT_$($documentationMatches.Count)"
      $registryFailures += "DOCUMENTATION_HANDOFF_COUNT_INVALID:$($documentationMatches.Count)"
    }

    $knowledgeMatches = @($registry.agents | Where-Object { $_.agent_id -eq 'knowledge_researcher' })

    if ($knowledgeMatches.Count -eq 1) {
      $knowledge = $knowledgeMatches[0]

      if (($knowledge.runtime_enabled -eq $false) -and ($knowledge.runtime_mode -eq 'admission_required')) {
        $knowledgeResearcherState = 'ADMISSION_REQUIRED_PROMOTION_ELIGIBLE'
      }
      elseif (($knowledge.runtime_enabled -eq $true) -and ($knowledge.runtime_mode -eq 'read_only_report_only')) {
        $knowledgeResearcherState = 'ALREADY_ENABLED_STOP_NO_REAPPLY'
        $registryFailures += 'KNOWLEDGE_RESEARCHER_ALREADY_ENABLED'
      }
      else {
        $knowledgeResearcherState = "UNEXPECTED_STATE:$($knowledge.runtime_enabled):$($knowledge.runtime_mode)"
        $registryFailures += 'KNOWLEDGE_RESEARCHER_STATE_UNEXPECTED'
      }
    }

    foreach ($agentId in @('coordinator', 'sovereignty_reviewer')) {
      $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

      if ($matches.Count -eq 1) {
        $agent = $matches[0]

        if (($agent.runtime_enabled -ne $true) -or ($agent.runtime_mode -ne 'read_only_report_only')) {
          $registryFailures += "EXISTING_AGENT_RUNTIME_STATE_UNEXPECTED:${agentId}"
        }
      }
    }
  }
}

"PROJECT_ROOT=$Root"
"REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
"MISSING_FILE_COUNT=$($missingFiles.Count)"
"MISSING_FILES=$([string]::Join(';', $missingFiles))"
"DOCUMENTATION_HANDOFF_REGISTRY_STATE=$documentationState"
"KNOWLEDGE_RESEARCHER_REGISTRY_STATE=$knowledgeResearcherState"
"REGISTRY_FAILURE_COUNT=$($registryFailures.Count)"
"REGISTRY_FAILURES=$([string]::Join(';', $registryFailures))"
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'

if (($missingFiles.Count -eq 0) -and ($registryFailures.Count -eq 0)) {
  'PREFLIGHT_RESULT=PASS'
  exit 0
}

'PREFLIGHT_RESULT=FAIL'
exit 1
