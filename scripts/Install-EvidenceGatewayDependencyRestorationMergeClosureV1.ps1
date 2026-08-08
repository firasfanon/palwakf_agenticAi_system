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

if (-not (Test-Path -LiteralPath $Target)) {
  throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target"
}

$copyPlan = @(
  @{
    source = 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'
    target = 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'
    label = 'Restore merged evidence and exact-output runtime module'
  },
  @{
    source = 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'
    target = 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'
    label = 'Restore exact-output contract schema'
  },
  @{
    source = 'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1'
    target = 'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1'
    label = 'Restore evidence gateway dependency contract'
  },
  @{
    source = 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'
    target = 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'
    label = 'Restore constrained read-only runner'
  },
  @{
    source = 'scripts\Test-ExactOutputBoundaryTrailingTextClosureV1.ps1'
    target = 'scripts\Test-ExactOutputBoundaryTrailingTextClosureV1.ps1'
    label = 'Restore exact-output static test'
  },
  @{
    source = 'scripts\Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1'
    target = 'scripts\Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1'
    label = 'Restore exact-output deterministic evaluations'
  },
  @{
    source = 'scripts\Test-EvidenceGatewayDependencyRestorationMergeClosureV1.ps1'
    target = 'scripts\Test-EvidenceGatewayDependencyRestorationMergeClosureV1.ps1'
    label = 'Add evidence gateway dependency test'
  },
  @{
    source = 'scripts\Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1'
    target = 'scripts\Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1'
    label = 'Restore baseline read-only deterministic evaluations'
  },
  @{
    source = 'governance\evidence_gateway_dependency_restoration\EVIDENCE_GATEWAY_DEPENDENCY_RESTORATION_POLICY_V1.md'
    target = 'governance\evidence_gateway_dependency_restoration\EVIDENCE_GATEWAY_DEPENDENCY_RESTORATION_POLICY_V1.md'
    label = 'Add dependency restoration policy'
  },
  @{
    source = 'README_AR.md'
    target = 'README_EVIDENCE_GATEWAY_DEPENDENCY_RESTORATION_MERGE_CLOSURE_V1_AR.md'
    label = 'Add closure readme'
  },
  @{
    source = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'
    target = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'
    label = 'Update root-cause record'
  },
  @{
    source = 'MANIFEST.md'
    target = 'MANIFEST_EVIDENCE_GATEWAY_DEPENDENCY_RESTORATION_MERGE_CLOSURE_V1.md'
    label = 'Add closure manifest'
  }
)

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\evidence_gateway_dependency_restoration_merge_$stamp"

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if (-not (Test-Path -LiteralPath $source)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$source"
  }

  if (Test-Path -LiteralPath $destination) {
    $backupPath = Join-Path $backupRoot $entry.target
    $backupDirectory = Split-Path -Parent $backupPath

    if ($PSCmdlet.ShouldProcess($backupDirectory, 'Create upgrade rollback directory when needed')) {
      New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    }

    if ($PSCmdlet.ShouldProcess($backupPath, "Backup current file before: $($entry.label)")) {
      Copy-Item -LiteralPath $destination -Destination $backupPath -Force
    }
  }

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, $entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

"INSTALL_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count)"
"BACKUP_PATH=$backupRoot"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'NEXT_STEP=RUN_STATIC_AND_DETERMINISTIC_TESTS_ONLY'
