[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

# Package syntax is verified separately before this target preflight.
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$requiredFiles = @(
  'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json',
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md'
)

$missing = @()

foreach ($relative in $requiredFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missing += $relative
  }
}

$registryAgentFailures = @()

if ($missing.Count -eq 0) {
  $registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

  if ($null -eq $registry.agents) {
    $registryAgentFailures += 'REGISTRY_AGENTS_ARRAY_MISSING'
  }
  else {
    foreach ($agentId in @(
      'coordinator',
      'sovereignty_reviewer',
      'knowledge_researcher',
      'documentation_handoff'
    )) {
      $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

      if ($matches.Count -ne 1) {
        $registryAgentFailures += "REGISTRY_AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
      }
    }
  }
}

"PROJECT_ROOT=$Root"
"REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$([string]::Join(';', $missing))"
"REGISTRY_AGENT_FAILURE_COUNT=$($registryAgentFailures.Count)"
"REGISTRY_AGENT_FAILURES=$([string]::Join(';', $registryAgentFailures))"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'

if (($missing.Count -eq 0) -and ($registryAgentFailures.Count -eq 0)) {
  'PREFLIGHT_RESULT=PASS'
  exit 0
}

'PREFLIGHT_RESULT=FAIL'
exit 1
