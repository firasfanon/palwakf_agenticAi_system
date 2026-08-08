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
  'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01PreflightV1_2.ps1',
  'scripts\Install-ReadOnlyAnalysisPack01V1_2.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1',
  'scripts\New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1',
  'scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1'
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

  foreach ($agentId in @('coordinator', 'sovereignty_reviewer', 'knowledge_researcher', 'documentation_handoff')) {
    $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

    if ($matches.Count -ne 1) {
      $registryFailures += "AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
      continue
    }

    $agent = $matches[0]

    if (($agent.runtime_enabled -ne $true) -or ($agent.runtime_mode -ne 'read_only_report_only')) {
      $registryFailures += "RUNTIME_STATE_INVALID:${agentId}"
    }

    if (@($agent.allowed_skills) -notcontains 'task_triage') {
      $registryFailures += "TASK_TRIAGE_MISSING:${agentId}"
    }

    if (@($agent.allowed_skills) -notcontains 'evidence_assessment') {
      $registryFailures += "EVIDENCE_ASSESSMENT_MISSING:${agentId}"
    }

    if (@($agent.allowed_autonomy) -notcontains 'L0_READ_ONLY') {
      $registryFailures += "L0_READ_ONLY_MISSING:${agentId}"
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

    foreach ($forbidden in @('sql_execute', 'git_write', 'file_modify_outside_output', 'deployment', 'secret_read')) {
      if (@($documentation.forbidden_capabilities) -notcontains $forbidden) {
        $registryFailures += "DOCUMENTATION_HANDOFF_FORBIDDEN_CAPABILITY_MISSING:${forbidden}"
      }
    }
  }
}

$packOwnedScripts = @(
  'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01PreflightV1_2.ps1',
  'scripts\Install-ReadOnlyAnalysisPack01V1_2.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1',
  'scripts\New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1',
  'scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1'
)

$parseFailures = @()
$unsafeInterpolationFailures = @()
$validScopes = @('env', 'script', 'global', 'local', 'private', 'using')

foreach ($relative in $packOwnedScripts) {
  $scriptPath = Join-Path $Root $relative

  if (-not (Test-Path -LiteralPath $scriptPath)) {
    continue
  }

  $tokens = $null
  $errors = $null

  [void][System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$errors
  )

  foreach ($error in @($errors)) {
    $parseFailures += "${relative}:$($error.Extent.StartLineNumber):$($error.Message)"
  }

  $scriptText = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8

  foreach ($match in [regex]::Matches($scriptText, '\$(?<name>[A-Za-z_][A-Za-z0-9_]*):')) {
    $name = [string]$match.Groups['name'].Value

    if ($validScopes -notcontains $name) {
      $unsafeInterpolationFailures += "${relative}:$($match.Value)"
    }
  }
}

"REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
"MISSING_FILE_COUNT=$($missingFiles.Count)"
"MISSING_FILES=$([string]::Join(';', $missingFiles))"
"REGISTRY_FAILURE_COUNT=$($registryFailures.Count)"
"REGISTRY_FAILURES=$([string]::Join(';', $registryFailures))"
"VALIDATION_SCOPE=PACK01_OWNED_SCRIPTS_ONLY"
"PACK_OWNED_SCRIPT_COUNT=$($packOwnedScripts.Count)"
"POWERSHELL_PARSE_FAILURE_COUNT=$($parseFailures.Count)"
"POWERSHELL_PARSE_FAILURES=$([string]::Join(';', $parseFailures))"
"VALID_VARIABLE_SCOPES_ALLOWED=$([string]::Join(',', $validScopes))"
"UNSAFE_VARIABLE_COLON_INTERPOLATION_COUNT=$($unsafeInterpolationFailures.Count)"
"UNSAFE_VARIABLE_COLON_INTERPOLATIONS=$([string]::Join(';', $unsafeInterpolationFailures))"
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'

if (
  ($missingFiles.Count -eq 0) -and
  ($registryFailures.Count -eq 0) -and
  ($parseFailures.Count -eq 0) -and
  ($unsafeInterpolationFailures.Count -eq 0)
) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
