[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [ValidateSet('Upgrade')][string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)
$registryPath = Join-Path $Target 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if (-not (Test-Path -LiteralPath $registryPath)) {
  throw "TARGET_REGISTRY_NOT_FOUND=$registryPath"
}

$requiredTargetFiles = @(
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1'
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

$registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
$knowledgeMatches = @($registry.agents | Where-Object { $_.agent_id -eq 'knowledge_researcher' })
$documentationMatches = @($registry.agents | Where-Object { $_.agent_id -eq 'documentation_handoff' })

if ($knowledgeMatches.Count -ne 1) {
  throw "TARGET_KNOWLEDGE_RESEARCHER_COUNT_INVALID=$($knowledgeMatches.Count)"
}

if ($documentationMatches.Count -ne 1) {
  throw "TARGET_DOCUMENTATION_HANDOFF_COUNT_INVALID=$($documentationMatches.Count)"
}

$knowledge = $knowledgeMatches[0]
$documentation = $documentationMatches[0]

if (($knowledge.runtime_enabled -ne $true) -or ($knowledge.runtime_mode -ne 'read_only_report_only')) {
  throw 'TARGET_KNOWLEDGE_RESEARCHER_RUNTIME_STATE_UNEXPECTED'
}

if (($documentation.runtime_enabled -ne $true) -or ($documentation.runtime_mode -ne 'read_only_report_only')) {
  throw 'TARGET_DOCUMENTATION_HANDOFF_RUNTIME_STATE_UNEXPECTED'
}

if (@($knowledge.allowed_skills) -notcontains 'knowledge_source_review') {
  throw 'TARGET_KNOWLEDGE_SOURCE_REVIEW_SKILL_MISSING'
}

if (@($documentation.allowed_skills) -contains 'documentation_handoff') {
  throw 'TARGET_DOCUMENTATION_HANDOFF_SKILL_ALREADY_PRESENT'
}

$copyPlan = @(
  @{ source = 'runtime\StructuredAnalysisPayloadV1.psm1'; target = 'runtime\StructuredAnalysisPayloadV1.psm1'; label = 'Add structured payload validator module' },
  @{ source = 'scripts\Invoke-StructuredAnalysisPayloadEvidenceRunnerV1.ps1'; target = 'scripts\Invoke-StructuredAnalysisPayloadEvidenceRunnerV1.ps1'; label = 'Add structured payload read-only runner' },
  @{ source = 'scripts\Test-StructuredAnalysisPayloadFoundationV1.ps1'; target = 'scripts\Test-StructuredAnalysisPayloadFoundationV1.ps1'; label = 'Add structured payload static validator' },
  @{ source = 'scripts\Test-StructuredAnalysisPayloadFoundationPackageSyntaxV1.ps1'; target = 'scripts\Test-StructuredAnalysisPayloadFoundationPackageSyntaxV1.ps1'; label = 'Add package syntax gate' },
  @{ source = 'scripts\Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1'; target = 'scripts\Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1'; label = 'Add structured payload deterministic evals' },
  @{ source = 'scripts\New-StructuredAnalysisPayloadPilotTasksV1.ps1'; target = 'scripts\New-StructuredAnalysisPayloadPilotTasksV1.ps1'; label = 'Add pending-only pilot task generator' },
  @{ source = 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_KNOWLEDGE_RESEARCHER_V1.json'; target = 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_KNOWLEDGE_RESEARCHER_V1.json'; label = 'Add knowledge payload contract' },
  @{ source = 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_DOCUMENTATION_HANDOFF_V1.json'; target = 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_DOCUMENTATION_HANDOFF_V1.json'; label = 'Add documentation payload contract' },
  @{ source = 'agents\output_profiles\structured_analysis_payload_foundation\knowledge_researcher.json'; target = 'agents\output_profiles\structured_analysis_payload_foundation\knowledge_researcher.json'; label = 'Add knowledge output profile' },
  @{ source = 'agents\output_profiles\structured_analysis_payload_foundation\documentation_handoff.json'; target = 'agents\output_profiles\structured_analysis_payload_foundation\documentation_handoff.json'; label = 'Add documentation output profile' },
  @{ source = 'agents\charters\structured_analysis_payload_foundation\KNOWLEDGE_RESEARCHER_STRUCTURED_PAYLOAD_V1.md'; target = 'agents\charters\structured_analysis_payload_foundation\KNOWLEDGE_RESEARCHER_STRUCTURED_PAYLOAD_V1.md'; label = 'Add knowledge structured charter' },
  @{ source = 'agents\charters\structured_analysis_payload_foundation\DOCUMENTATION_HANDOFF_STRUCTURED_PAYLOAD_V1.md'; target = 'agents\charters\structured_analysis_payload_foundation\DOCUMENTATION_HANDOFF_STRUCTURED_PAYLOAD_V1.md'; label = 'Add documentation structured charter' },
  @{ source = 'tasks\templates\structured_analysis_payload_foundation\SAPF_KNOWLEDGE_RESEARCH_PILOT_001.json'; target = 'tasks\templates\structured_analysis_payload_foundation\SAPF_KNOWLEDGE_RESEARCH_PILOT_001.json'; label = 'Add knowledge pending pilot template' },
  @{ source = 'tasks\templates\structured_analysis_payload_foundation\SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json'; target = 'tasks\templates\structured_analysis_payload_foundation\SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json'; label = 'Add documentation pending pilot template' },
  @{ source = 'governance\structured_analysis_payload_foundation\STRUCTURED_ANALYSIS_PAYLOAD_POLICY_V1.md'; target = 'governance\structured_analysis_payload_foundation\STRUCTURED_ANALYSIS_PAYLOAD_POLICY_V1.md'; label = 'Add payload governance policy' },
  @{ source = 'governance\structured_analysis_payload_foundation\PAYLOAD_VALIDATION_AND_HOST_ENVELOPE_POLICY_V1.md'; target = 'governance\structured_analysis_payload_foundation\PAYLOAD_VALIDATION_AND_HOST_ENVELOPE_POLICY_V1.md'; label = 'Add payload validation and host envelope policy' },
  @{ source = 'evals\structured_analysis_payload_foundation\cases\VALID_KNOWLEDGE_V1.json'; target = 'evals\structured_analysis_payload_foundation\cases\VALID_KNOWLEDGE_V1.json'; label = 'Add valid knowledge eval fixture' },
  @{ source = 'evals\structured_analysis_payload_foundation\cases\VALID_DOCUMENTATION_V1.json'; target = 'evals\structured_analysis_payload_foundation\cases\VALID_DOCUMENTATION_V1.json'; label = 'Add valid documentation eval fixture' },
  @{ source = 'evals\structured_analysis_payload_foundation\cases\INVALID_EXTRA_FIELD_V1.json'; target = 'evals\structured_analysis_payload_foundation\cases\INVALID_EXTRA_FIELD_V1.json'; label = 'Add extra-field rejection eval fixture' },
  @{ source = 'evals\structured_analysis_payload_foundation\cases\INVALID_UNEXPECTED_EVIDENCE_V1.json'; target = 'evals\structured_analysis_payload_foundation\cases\INVALID_UNEXPECTED_EVIDENCE_V1.json'; label = 'Add unexpected-evidence rejection eval fixture' },
  @{ source = 'evals\structured_analysis_payload_foundation\cases\INVALID_HANDOFF_MISSING_REFERENCE_V1.json'; target = 'evals\structured_analysis_payload_foundation\cases\INVALID_HANDOFF_MISSING_REFERENCE_V1.json'; label = 'Add handoff-reference rejection eval fixture' },
  @{ source = 'evals\structured_analysis_payload_foundation\cases\INVALID_KNOWLEDGE_MISSING_ASSESSMENT_V1.json'; target = 'evals\structured_analysis_payload_foundation\cases\INVALID_KNOWLEDGE_MISSING_ASSESSMENT_V1.json'; label = 'Add source-assessment rejection eval fixture' },
  @{ source = 'README_AR.md'; target = 'README_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_AR.md'; label = 'Add Arabic package readme' },
  @{ source = 'APPLY_GUIDE_AR.md'; target = 'APPLY_GUIDE_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_AR.md'; label = 'Add Arabic apply guide' },
  @{ source = 'ERROR_RECORD_AR.md'; target = 'ERROR_RECORD_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_AR.md'; label = 'Add error record' },
  @{ source = 'SESSION_HANDOFF_AR.md'; target = 'SESSION_HANDOFF_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_AR.md'; label = 'Add candidate session handoff' },
  @{ source = 'MANIFEST.md'; target = 'MANIFEST_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1.md'; label = 'Add package manifest' },
  @{ source = 'PROJECT_STATUS_CANDIDATE_AR.md'; target = 'PROJECT_STATUS_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_AR.md'; label = 'Add candidate status' }
)

foreach ($entry in $copyPlan) {
  $sourcePath = Join-Path $SourceRoot $entry.source

  if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$sourcePath"
  }
}

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\structured_analysis_payload_foundation_v1_$stamp"
$registryBackupPath = Join-Path $backupRoot 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if ($PSCmdlet.ShouldProcess((Split-Path -Parent $registryBackupPath), 'Create structured payload registry backup directory')) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $registryBackupPath) -Force | Out-Null
}

if ($PSCmdlet.ShouldProcess($registryBackupPath, 'Backup registry before structured payload skill admission')) {
  Copy-Item -LiteralPath $registryPath -Destination $registryBackupPath -Force
}

foreach ($entry in $copyPlan) {
  $sourcePath = Join-Path $SourceRoot $entry.source
  $destinationPath = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destinationPath

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create structured payload target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destinationPath, $entry.label)) {
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
  }
}

$skillCandidates = @($documentation.allowed_skills) + @('documentation_handoff')
$documentation.allowed_skills = @(
  $skillCandidates |
    Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
    Select-Object -Unique
)

if ($PSCmdlet.ShouldProcess($registryPath, 'Admit documentation_handoff skill for L0 read-only structured payload output only')) {
  $registry | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $registryPath -Encoding UTF8
}

"INSTALL_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count + 2)"
"BACKUP_PATH=$backupRoot"
'REGISTRY_MUTATION=DOCUMENTATION_HANDOFF_SKILL_ONLY'
'CORE_RUNTIME_MUTATION=NONE'
'CORE_11_LINE_CONTRACT_MUTATION=NONE'
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
'NEXT_STEP=RUN_POST_INSTALL_STATIC_TEST_AND_DETERMINISTIC_EVALS_ONLY'
