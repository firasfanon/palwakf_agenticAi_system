[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$requiredFiles = @(
  'runtime\StructuredAnalysisPayloadV1.psm1',
  'scripts\Invoke-StructuredAnalysisPayloadEvidenceRunnerV1.ps1',
  'scripts\Test-StructuredAnalysisPayloadFoundationV1.ps1',
  'scripts\Test-StructuredAnalysisPayloadFoundationPackageSyntaxV1.ps1',
  'scripts\Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1',
  'scripts\New-StructuredAnalysisPayloadPilotTasksV1.ps1',
  'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_KNOWLEDGE_RESEARCHER_V1.json',
  'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_DOCUMENTATION_HANDOFF_V1.json',
  'agents\output_profiles\structured_analysis_payload_foundation\knowledge_researcher.json',
  'agents\output_profiles\structured_analysis_payload_foundation\documentation_handoff.json',
  'agents\charters\structured_analysis_payload_foundation\KNOWLEDGE_RESEARCHER_STRUCTURED_PAYLOAD_V1.md',
  'agents\charters\structured_analysis_payload_foundation\DOCUMENTATION_HANDOFF_STRUCTURED_PAYLOAD_V1.md',
  'tasks\templates\structured_analysis_payload_foundation\SAPF_KNOWLEDGE_RESEARCH_PILOT_001.json',
  'tasks\templates\structured_analysis_payload_foundation\SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json',
  'governance\structured_analysis_payload_foundation\STRUCTURED_ANALYSIS_PAYLOAD_POLICY_V1.md',
  'governance\structured_analysis_payload_foundation\PAYLOAD_VALIDATION_AND_HOST_ENVELOPE_POLICY_V1.md',
  'evals\structured_analysis_payload_foundation\cases\VALID_KNOWLEDGE_V1.json',
  'evals\structured_analysis_payload_foundation\cases\VALID_DOCUMENTATION_V1.json',
  'evals\structured_analysis_payload_foundation\cases\INVALID_EXTRA_FIELD_V1.json',
  'evals\structured_analysis_payload_foundation\cases\INVALID_UNEXPECTED_EVIDENCE_V1.json',
  'evals\structured_analysis_payload_foundation\cases\INVALID_HANDOFF_MISSING_REFERENCE_V1.json',
  'evals\structured_analysis_payload_foundation\cases\INVALID_KNOWLEDGE_MISSING_ASSESSMENT_V1.json'
)

$missingFiles = @()

foreach ($relative in $requiredFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missingFiles += $relative
  }
}

$validationFailures = @()

if ($missingFiles.Count -eq 0) {
  $registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

  $knowledge = @($registry.agents | Where-Object { $_.agent_id -eq 'knowledge_researcher' })
  $documentation = @($registry.agents | Where-Object { $_.agent_id -eq 'documentation_handoff' })

  if ($knowledge.Count -ne 1) {
    $validationFailures += 'KNOWLEDGE_RESEARCHER_COUNT_INVALID'
  }

  if ($documentation.Count -ne 1) {
    $validationFailures += 'DOCUMENTATION_HANDOFF_COUNT_INVALID'
  }

  foreach ($agent in @($knowledge + $documentation)) {
    if (($agent.runtime_enabled -ne $true) -or ($agent.runtime_mode -ne 'read_only_report_only')) {
      $validationFailures += "RUNTIME_STATE_INVALID:$($agent.agent_id)"
    }

    if (@($agent.allowed_autonomy) -notcontains 'L0_READ_ONLY') {
      $validationFailures += "L0_READ_ONLY_MISSING:$($agent.agent_id)"
    }
  }

  if (($knowledge.Count -eq 1) -and (@($knowledge[0].allowed_skills) -notcontains 'knowledge_source_review')) {
    $validationFailures += 'KNOWLEDGE_SOURCE_REVIEW_SKILL_MISSING'
  }

  if (($documentation.Count -eq 1) -and (@($documentation[0].allowed_skills) -notcontains 'documentation_handoff')) {
    $validationFailures += 'DOCUMENTATION_HANDOFF_SKILL_MISSING'
  }

  foreach ($contractPath in @(
    (Join-Path $Root 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_KNOWLEDGE_RESEARCHER_V1.json'),
    (Join-Path $Root 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_DOCUMENTATION_HANDOFF_V1.json')
  )) {
    try {
      $contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
      if (($contract.raw_output_format -ne 'SINGLE_JSON_OBJECT') -or ($contract.additional_keys_allowed -ne $false)) {
        $validationFailures += "PAYLOAD_CONTRACT_INVALID:$contractPath"
      }
    }
    catch {
      $validationFailures += "PAYLOAD_CONTRACT_PARSE_FAILED:$contractPath"
    }
  }

  $modulePath = Join-Path $Root 'runtime\StructuredAnalysisPayloadV1.psm1'
  Import-Module $modulePath -Force

  if ($null -eq (Get-Command -Name 'Test-StructuredAnalysisPayloadV1' -ErrorAction SilentlyContinue)) {
    $validationFailures += 'PAYLOAD_VALIDATOR_FUNCTION_UNAVAILABLE'
  }
}

"REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
"MISSING_FILE_COUNT=$($missingFiles.Count)"
"MISSING_FILES=$([string]::Join(';', $missingFiles))"
"VALIDATION_FAILURE_COUNT=$($validationFailures.Count)"
"VALIDATION_FAILURES=$([string]::Join(';', $validationFailures))"
'CORE_RUNTIME_MUTATION=NONE'
'CORE_11_LINE_CONTRACT_MUTATION=NONE'
'REGISTRY_MUTATION=DOCUMENTATION_HANDOFF_SKILL_ONLY'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'

if (($missingFiles.Count -eq 0) -and ($validationFailures.Count -eq 0)) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
