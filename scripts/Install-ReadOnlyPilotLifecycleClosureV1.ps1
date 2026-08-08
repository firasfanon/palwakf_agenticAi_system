[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [ValidateSet('Upgrade')][string]$Mode='Upgrade'
)
$ErrorActionPreference='Stop'
$SourceRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @(
  'scripts\Test-StructuredAnalysisPayloadFoundationV1.ps1',
  'scripts\Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1',
  'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1',
  'scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1',
  'tasks\approved\PILOT_READ_ONLY_CONTEXT_EVIDENCE_001.json'
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Target $_)) })
if ($missing.Count -gt 0) { throw "TARGET_BASELINE_MISSING=$([string]::Join(';',$missing))" }

$copyPlan = @(
  @{source='scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1';target='scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1';label='Add human review decision writer'},
  @{source='scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1';target='scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1';label='Add approved task archive transition'},
  @{source='scripts\Test-ReadOnlyPilotActiveStateV1.ps1';target='scripts\Test-ReadOnlyPilotActiveStateV1.ps1';label='Add active pilot state checker'},
  @{source='scripts\Test-ReadOnlyPilotLifecycleClosureV1.ps1';target='scripts\Test-ReadOnlyPilotLifecycleClosureV1.ps1';label='Add lifecycle closure static test'},
  @{source='scripts\Test-ReadOnlyPilotLifecycleClosurePackageSyntaxV1.ps1';target='scripts\Test-ReadOnlyPilotLifecycleClosurePackageSyntaxV1.ps1';label='Add lifecycle closure package syntax gate'},
  @{source='scripts\Test-ReadOnlyPilotLifecycleClosurePreflightV1.ps1';target='scripts\Test-ReadOnlyPilotLifecycleClosurePreflightV1.ps1';label='Add lifecycle closure preflight'},
  @{source='scripts\Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1';target='scripts\Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1';label='Add lifecycle closure deterministic evals'},
  @{source='task_contracts\READ_ONLY_PILOT_HUMAN_REVIEW_DECISION_V1.json';target='task_contracts\READ_ONLY_PILOT_HUMAN_REVIEW_DECISION_V1.json';label='Add human review decision contract'},
  @{source='governance\read_only_pilot_lifecycle_closure\READ_ONLY_PILOT_HUMAN_REVIEW_AND_ARCHIVE_POLICY_V1.md';target='governance\read_only_pilot_lifecycle_closure\READ_ONLY_PILOT_HUMAN_REVIEW_AND_ARCHIVE_POLICY_V1.md';label='Add review and archive policy'},
  @{source='governance\read_only_pilot_lifecycle_closure\DECISION_RECORD_CONTRACT_V1.md';target='governance\read_only_pilot_lifecycle_closure\DECISION_RECORD_CONTRACT_V1.md';label='Add decision record contract'},
  @{source='README_AR.md';target='README_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_AR.md';label='Add lifecycle closure readme'},
  @{source='APPLY_GUIDE_AR.md';target='APPLY_GUIDE_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_AR.md';label='Add lifecycle closure apply guide'},
  @{source='SESSION_HANDOFF_AR.md';target='SESSION_HANDOFF_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_AR.md';label='Add lifecycle closure handoff'},
  @{source='ERROR_RECORD_AR.md';target='ERROR_RECORD_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_AR.md';label='Add lifecycle closure error record'},
  @{source='PROJECT_STATUS_CANDIDATE_AR.md';target='PROJECT_STATUS_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_AR.md';label='Add lifecycle closure candidate status'},
  @{source='CHANGELOG_CANDIDATE.md';target='CHANGELOG_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1.md';label='Add lifecycle closure changelog'}
)
foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "PACKAGE_SOURCE_NOT_FOUND=$source" }
}

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\read_only_pilot_lifecycle_closure_v1_$stamp"
$backupManifestPath = Join-Path $backupRoot 'install_preimage_manifest.json'
$backupEntries = @()
foreach ($entry in $copyPlan) {
  $destination = Join-Path $Target $entry.target
  $backupEntries += [ordered]@{
    target_relative_path = $entry.target
    target_existed_before_apply = [bool](Test-Path -LiteralPath $destination -PathType Leaf)
  }
}

if ($PSCmdlet.ShouldProcess($backupRoot,'Create lifecycle-closure install backup directory')) {
  New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
}
foreach ($entry in $copyPlan) {
  $destination = Join-Path $Target $entry.target
  if (Test-Path -LiteralPath $destination -PathType Leaf) {
    $backupDestination = Join-Path $backupRoot $entry.target
    if ($PSCmdlet.ShouldProcess($backupDestination,'Backup existing lifecycle-closure target preimage')) {
      New-Item -ItemType Directory -Path (Split-Path -Parent $backupDestination) -Force | Out-Null
      Copy-Item -LiteralPath $destination -Destination $backupDestination -Force
    }
  }
}
$backupManifest = [ordered]@{
  record_type = 'LIFECYCLE_CLOSURE_INSTALL_PREIMAGE_MANIFEST'
  created_at_utc = [DateTime]::UtcNow.ToString('o')
  package = 'LOCAL_AGENT_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_2_REVC'
  install_mode = $Mode
  backup_strategy = 'PREIMAGE_COPY_OF_EXISTING_TARGETS'
  entries = $backupEntries
}
if ($PSCmdlet.ShouldProcess($backupManifestPath,'Write lifecycle-closure install backup manifest')) {
  $backupManifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $backupManifestPath -Encoding UTF8
}

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $directory = Split-Path -Parent $destination
  if ($PSCmdlet.ShouldProcess($directory,'Create lifecycle closure target directory when needed')) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
  }
  if ($PSCmdlet.ShouldProcess($destination,$entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

$installStatus = if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' }
$backupStatus = if ($WhatIfPreference) { 'PLANNED' } else { 'COMPLETE' }
"INSTALL_STATUS=$installStatus"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count)"
"BACKUP_PATH=$backupRoot"
"BACKUP_MANIFEST_PATH=$backupManifestPath"
"BACKUP_STATUS=$backupStatus"
'INSTALL_BACKUP_STRATEGY=PREIMAGE_COPY_OF_EXISTING_TARGETS'
'REGISTRY_MUTATION=NONE'
'CORE_RUNTIME_MUTATION=NONE'
'CORE_11_LINE_CONTRACT_MUTATION=NONE'
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PILOT_TASK_GENERATION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
'NEXT_STEP=RUN_POST_INSTALL_STATIC_TEST_AND_DETERMINISTIC_EVALS_ONLY'
