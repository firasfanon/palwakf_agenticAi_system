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
  'reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md',
  'scripts\Test-ReadOnlyAnalysisPack01V1_2.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1'
)

$missingFiles = @()
foreach ($relative in $requiredFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missingFiles += $relative
  }
}

$registryFailures = @()

if ($missingFiles.Count -eq 0) {
  $registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

  if ($registry.registry_version -ne '1.0') {
    $registryFailures += "REGISTRY_VERSION_INVALID:$($registry.registry_version)"
  }

  if ($registry.execution_default -ne 'disabled') {
    $registryFailures += "EXECUTION_DEFAULT_INVALID:$($registry.execution_default)"
  }

  foreach ($agentId in @('coordinator', 'sovereignty_reviewer', 'knowledge_researcher', 'documentation_handoff')) {
    $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

    if ($matches.Count -ne 1) {
      $registryFailures += "PACK_AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
      continue
    }

    $agent = $matches[0]

    if (($agent.runtime_enabled -ne $true) -or ($agent.runtime_mode -ne 'read_only_report_only')) {
      $registryFailures += "PACK_AGENT_RUNTIME_STATE_INVALID:${agentId}"
    }

    if (@($agent.allowed_skills) -notcontains 'task_triage') {
      $registryFailures += "PACK_AGENT_TASK_TRIAGE_MISSING:${agentId}"
    }

    if (@($agent.allowed_skills) -notcontains 'evidence_assessment') {
      $registryFailures += "PACK_AGENT_EVIDENCE_ASSESSMENT_MISSING:${agentId}"
    }

    if (@($agent.allowed_autonomy) -notcontains 'L0_READ_ONLY') {
      $registryFailures += "PACK_AGENT_L0_READ_ONLY_MISSING:${agentId}"
    }
  }

  $documentation = @($registry.agents | Where-Object { $_.agent_id -eq 'documentation_handoff' })[0]

  if ($null -ne $documentation) {
    $expectedProperties = @(
      'agent_id',
      'allowed_autonomy',
      'runtime_enabled',
      'runtime_mode',
      'allowed_skills',
      'forbidden_capabilities'
    )

    $actualProperties = @($documentation.PSObject.Properties.Name | Sort-Object)
    $expectedSorted = @($expectedProperties | Sort-Object)

    if (([string]::Join('|', $actualProperties)) -ne ([string]::Join('|', $expectedSorted))) {
      $registryFailures += 'DOCUMENTATION_HANDOFF_SCHEMA_MISMATCH'
    }
  }
}

"PROJECT_ROOT=$Root"
"REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
"MISSING_FILE_COUNT=$($missingFiles.Count)"
"MISSING_FILES=$([string]::Join(';', $missingFiles))"
"REGISTRY_FAILURE_COUNT=$($registryFailures.Count)"
"REGISTRY_FAILURES=$([string]::Join(';', $registryFailures))"
'VALIDATION_SCOPE=PACK01_OWNED_ARTIFACTS_AND_REGISTRY_ONLY'
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
