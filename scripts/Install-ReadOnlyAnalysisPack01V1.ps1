[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,

  [ValidateSet('Upgrade')]
  [string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'

# This installer must not copy or mutate the frozen core runtime files.
$SourceRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)

$requiredTargetFiles = @(
  'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json',
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md'
)

$missingTargetFiles = @()

foreach ($relative in $requiredTargetFiles) {
  if (-not (Test-Path -LiteralPath (Join-Path $Target $relative))) {
    $missingTargetFiles += $relative
  }
}

if ($missingTargetFiles.Count -gt 0) {
  throw "TARGET_BASELINE_MISSING=$([string]::Join(';', $missingTargetFiles))"
}

$registryPath = Join-Path $Target 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
$registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($null -eq $registry.agents) {
  throw 'TARGET_REGISTRY_AGENTS_ARRAY_MISSING'
}

$agentIds = @(
  'coordinator',
  'sovereignty_reviewer',
  'knowledge_researcher',
  'documentation_handoff'
)

foreach ($agentId in $agentIds) {
  $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

  if ($matches.Count -ne 1) {
    throw "TARGET_REGISTRY_AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
  }
}

$copyPlan = @(
  @{ source = 'agents\charters\read_only_analysis_pack_01\COORDINATOR_READ_ONLY_ANALYSIS_PACK_01.md'; target = 'agents\charters\read_only_analysis_pack_01\COORDINATOR_READ_ONLY_ANALYSIS_PACK_01.md'; label = 'Add coordinator Pack 01 charter' },
  @{ source = 'agents\charters\read_only_analysis_pack_01\SOVEREIGNTY_REVIEWER_READ_ONLY_ANALYSIS_PACK_01.md'; target = 'agents\charters\read_only_analysis_pack_01\SOVEREIGNTY_REVIEWER_READ_ONLY_ANALYSIS_PACK_01.md'; label = 'Add sovereignty reviewer Pack 01 charter' },
  @{ source = 'agents\charters\read_only_analysis_pack_01\KNOWLEDGE_RESEARCHER_READ_ONLY_ANALYSIS_PACK_01.md'; target = 'agents\charters\read_only_analysis_pack_01\KNOWLEDGE_RESEARCHER_READ_ONLY_ANALYSIS_PACK_01.md'; label = 'Add knowledge researcher Pack 01 charter' },
  @{ source = 'agents\charters\read_only_analysis_pack_01\DOCUMENTATION_HANDOFF_READ_ONLY_ANALYSIS_PACK_01.md'; target = 'agents\charters\read_only_analysis_pack_01\DOCUMENTATION_HANDOFF_READ_ONLY_ANALYSIS_PACK_01.md'; label = 'Add documentation handoff Pack 01 charter' },
  @{ source = 'agents\output_profiles\read_only_analysis_pack_01\coordinator.json'; target = 'agents\output_profiles\read_only_analysis_pack_01\coordinator.json'; label = 'Add coordinator Pack 01 profile' },
  @{ source = 'agents\output_profiles\read_only_analysis_pack_01\sovereignty_reviewer.json'; target = 'agents\output_profiles\read_only_analysis_pack_01\sovereignty_reviewer.json'; label = 'Add sovereignty reviewer Pack 01 profile' },
  @{ source = 'agents\output_profiles\read_only_analysis_pack_01\knowledge_researcher.json'; target = 'agents\output_profiles\read_only_analysis_pack_01\knowledge_researcher.json'; label = 'Add knowledge researcher Pack 01 profile' },
  @{ source = 'agents\output_profiles\read_only_analysis_pack_01\documentation_handoff.json'; target = 'agents\output_profiles\read_only_analysis_pack_01\documentation_handoff.json'; label = 'Add documentation handoff Pack 01 profile' },
  @{ source = 'tasks\templates\read_only_analysis_pack_01\PACK01_COORDINATOR_ROUTING_PILOT_001.json'; target = 'tasks\templates\read_only_analysis_pack_01\PACK01_COORDINATOR_ROUTING_PILOT_001.json'; label = 'Add coordinator Pilot template' },
  @{ source = 'tasks\templates\read_only_analysis_pack_01\PACK01_SOVEREIGNTY_REVIEW_PILOT_001.json'; target = 'tasks\templates\read_only_analysis_pack_01\PACK01_SOVEREIGNTY_REVIEW_PILOT_001.json'; label = 'Add sovereignty Pilot template' },
  @{ source = 'tasks\templates\read_only_analysis_pack_01\PACK01_KNOWLEDGE_RESEARCH_PILOT_001.json'; target = 'tasks\templates\read_only_analysis_pack_01\PACK01_KNOWLEDGE_RESEARCH_PILOT_001.json'; label = 'Add knowledge Pilot template' },
  @{ source = 'tasks\templates\read_only_analysis_pack_01\PACK01_DOCUMENTATION_HANDOFF_PILOT_001.json'; target = 'tasks\templates\read_only_analysis_pack_01\PACK01_DOCUMENTATION_HANDOFF_PILOT_001.json'; label = 'Add documentation Pilot template' },
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01PreflightV1.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01PreflightV1.ps1'; label = 'Add Pack 01 preflight test' },
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1'; label = 'Add Pack 01 package syntax gate' },
  @{ source = 'scripts\Enable-ReadOnlyAnalysisPack01AgentsV1.ps1'; target = 'scripts\Enable-ReadOnlyAnalysisPack01AgentsV1.ps1'; label = 'Add Pack 01 registry activation script' },
  @{ source = 'scripts\New-ReadOnlyAnalysisPack01PilotTasksV1.ps1'; target = 'scripts\New-ReadOnlyAnalysisPack01PilotTasksV1.ps1'; label = 'Add Pack 01 task generator' },
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01V1.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01V1.ps1'; label = 'Add Pack 01 static test' },
  @{ source = 'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1.ps1'; target = 'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1.ps1'; label = 'Add Pack 01 deterministic evals' },
  @{ source = 'scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1.ps1'; target = 'scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1.ps1'; label = 'Add Pack 01 registry rollback script' },
  @{ source = 'governance\read_only_analysis_pack_01\PACK_01_POLICY.md'; target = 'governance\read_only_analysis_pack_01\PACK_01_POLICY.md'; label = 'Add Pack 01 governance policy' },
  @{ source = 'README_AR.md'; target = 'README_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_AR.md'; label = 'Add Pack 01 Arabic readme' },
  @{ source = 'SCOPE_AND_LIMITATIONS_AR.md'; target = 'SCOPE_AND_LIMITATIONS_READ_ONLY_ANALYSIS_PACK_01_AR.md'; label = 'Add Pack 01 scope and limitations' },
  @{ source = 'MANIFEST.md'; target = 'MANIFEST_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01.md'; label = 'Add Pack 01 manifest' }
)

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source

  if (-not (Test-Path -LiteralPath $source)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$source"
  }
}

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\read_only_analysis_pack_01_$stamp"
$registryBackupPath = Join-Path $backupRoot 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if ($PSCmdlet.ShouldProcess((Split-Path -Parent $registryBackupPath), 'Create Pack 01 registry backup directory')) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $registryBackupPath) -Force | Out-Null
}

if ($PSCmdlet.ShouldProcess($registryBackupPath, 'Backup registry before enabling Pack 01 agents')) {
  Copy-Item -LiteralPath $registryPath -Destination $registryBackupPath -Force
}

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create Pack 01 target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, $entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

$activationScript = Join-Path $Target 'scripts\Enable-ReadOnlyAnalysisPack01AgentsV1.ps1'

if ($WhatIfPreference) {
  "PACK01_REGISTRY_ACTIVATION=WHATIF_NOT_EXECUTED"
}
else {
  & $activationScript -ProjectRoot $Target
}

"INSTALL_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count + 1)"
"BACKUP_PATH=$backupRoot"
"PACK_AGENT_COUNT=$($agentIds.Count)"
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'NEXT_STEP=RUN_PACK01_STATIC_AND_DETERMINISTIC_TESTS_ONLY'
