[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,

  [ValidateSet('Upgrade')]
  [string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)

function Get-UniqueStringList {
  param(
    [Parameter(Mandatory = $true)]
    [object[]]$Values
  )

  $seen = @{}
  $result = New-Object System.Collections.Generic.List[string]

  foreach ($value in @($Values)) {
    $text = [string]$value

    if ([string]::IsNullOrWhiteSpace($text)) {
      continue
    }

    if (-not $seen.ContainsKey($text)) {
      $seen[$text] = $true
      [void]$result.Add($text)
    }
  }

  return @($result.ToArray())
}

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

if (($registry.registry_version -ne '1.0') -or ($registry.execution_default -ne 'disabled')) {
  throw 'TARGET_REGISTRY_METADATA_UNEXPECTED'
}

foreach ($agentId in @('coordinator', 'sovereignty_reviewer', 'knowledge_researcher')) {
  $matches = @($registry.agents | Where-Object { $_.agent_id -eq $agentId })

  if ($matches.Count -ne 1) {
    throw "TARGET_REQUIRED_AGENT_COUNT_INVALID:${agentId}:$($matches.Count)"
  }
}

$documentationMatches = @($registry.agents | Where-Object { $_.agent_id -eq 'documentation_handoff' })

if ($documentationMatches.Count -ne 0) {
  throw "TARGET_DOCUMENTATION_HANDOFF_ALREADY_PRESENT_COUNT=$($documentationMatches.Count)"
}

$coordinator = @($registry.agents | Where-Object { $_.agent_id -eq 'coordinator' })[0]
$sovereigntyReviewer = @($registry.agents | Where-Object { $_.agent_id -eq 'sovereignty_reviewer' })[0]
$knowledgeResearcher = @($registry.agents | Where-Object { $_.agent_id -eq 'knowledge_researcher' })[0]

if (($coordinator.runtime_enabled -ne $true) -or ($coordinator.runtime_mode -ne 'read_only_report_only')) {
  throw 'TARGET_COORDINATOR_RUNTIME_STATE_UNEXPECTED'
}

if (($sovereigntyReviewer.runtime_enabled -ne $true) -or ($sovereigntyReviewer.runtime_mode -ne 'read_only_report_only')) {
  throw 'TARGET_SOVEREIGNTY_REVIEWER_RUNTIME_STATE_UNEXPECTED'
}

if (($knowledgeResearcher.runtime_enabled -ne $false) -or ($knowledgeResearcher.runtime_mode -ne 'admission_required')) {
  throw 'TARGET_KNOWLEDGE_RESEARCHER_ADMISSION_STATE_UNEXPECTED'
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
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1'; label = 'Add Pack 01 package syntax gate' },
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01PreflightV1_2.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01PreflightV1_2.ps1'; label = 'Add Pack 01 bootstrap preflight' },
  @{ source = 'scripts\Install-ReadOnlyAnalysisPack01V1_2.ps1'; target = 'scripts\Install-ReadOnlyAnalysisPack01V1_2.ps1'; label = 'Add Pack 01 bootstrap installer' },
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01V1_2.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01V1_2.ps1'; label = 'Add Pack 01 post-install static test' },
  @{ source = 'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1'; target = 'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1'; label = 'Add Pack 01 deterministic evals' },
  @{ source = 'scripts\New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1'; target = 'scripts\New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1'; label = 'Add Pack 01 task generator' },
  @{ source = 'scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1'; target = 'scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1'; label = 'Add Pack 01 registry rollback script' },
  @{ source = 'governance\read_only_analysis_pack_01\PACK_01_POLICY.md'; target = 'governance\read_only_analysis_pack_01\PACK_01_POLICY.md'; label = 'Add Pack 01 governance policy' },
  @{ source = 'governance\read_only_analysis_pack_01\REGISTRY_BOOTSTRAP_CONTRACT_V1_2.md'; target = 'governance\read_only_analysis_pack_01\REGISTRY_BOOTSTRAP_CONTRACT_V1_2.md'; label = 'Add Registry bootstrap contract' },
  @{ source = 'README_AR.md'; target = 'README_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_2_AR.md'; label = 'Add Pack 01 Arabic readme' },
  @{ source = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'; target = 'ROOT_CAUSE_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_2_AR.md'; label = 'Add Pack 01 remediation note' },
  @{ source = 'MANIFEST.md'; target = 'MANIFEST_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_2.md'; label = 'Add Pack 01 manifest' }
)

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source

  if (-not (Test-Path -LiteralPath $source)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$source"
  }
}

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\read_only_analysis_pack_01_v1_2_$stamp"
$registryBackupPath = Join-Path $backupRoot 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if ($PSCmdlet.ShouldProcess((Split-Path -Parent $registryBackupPath), 'Create Pack 01 V1.2 registry backup directory')) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $registryBackupPath) -Force | Out-Null
}

if ($PSCmdlet.ShouldProcess($registryBackupPath, 'Backup registry before Pack 01 V1.2 bootstrap')) {
  Copy-Item -LiteralPath $registryPath -Destination $registryBackupPath -Force
}

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create Pack 01 V1.2 target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, $entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

$documentationHandoff = [PSCustomObject]@{
  agent_id = 'documentation_handoff'
  allowed_autonomy = @('L0_READ_ONLY')
  runtime_enabled = $true
  runtime_mode = 'read_only_report_only'
  allowed_skills = @('task_triage', 'evidence_assessment')
  forbidden_capabilities = @(
    'sql_execute',
    'git_write',
    'file_modify_outside_output',
    'deployment',
    'secret_read'
  )
}

$updatedSovereigntySkills = Get-UniqueStringList -Values @(
  @($sovereigntyReviewer.allowed_skills) +
  @('task_triage', 'evidence_assessment')
)

$updatedKnowledgeSkills = Get-UniqueStringList -Values @(
  @($knowledgeResearcher.allowed_skills) +
  @('task_triage', 'evidence_assessment')
)

$sovereigntyReviewer.allowed_skills = $updatedSovereigntySkills
$knowledgeResearcher.allowed_skills = $updatedKnowledgeSkills
$knowledgeResearcher.runtime_enabled = $true
$knowledgeResearcher.runtime_mode = 'read_only_report_only'
$registry.agents = @($registry.agents) + @($documentationHandoff)

if ($PSCmdlet.ShouldProcess($registryPath, 'Bootstrap documentation_handoff and activate Pack 01 knowledge researcher')) {
  $registry |
    ConvertTo-Json -Depth 30 |
    Set-Content -LiteralPath $registryPath -Encoding UTF8
}

"INSTALL_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count + 2)"
"BACKUP_PATH=$backupRoot"
'DOCUMENTATION_HANDOFF_BOOTSTRAP=PLANNED_OR_APPLIED'
'KNOWLEDGE_RESEARCHER_ADMISSION_PROMOTION=PLANNED_OR_APPLIED'
'SOVEREIGNTY_REVIEWER_TASK_TRIAGE_SKILL=PLANNED_OR_APPLIED'
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'NEXT_STEP=RUN_PACK01_POST_INSTALL_STATIC_AND_DETERMINISTIC_TESTS_ONLY'
