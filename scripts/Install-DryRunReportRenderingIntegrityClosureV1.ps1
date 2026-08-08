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
$runnerTarget = Join-Path $Target 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'

if (-not (Test-Path -LiteralPath $Target)) {
  throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target"
}

if (-not (Test-Path -LiteralPath $runnerTarget)) {
  throw "TARGET_RUNNER_NOT_FOUND=$runnerTarget"
}

$copyPlan = @(
  @{
    source = 'scripts\Repair-DryRunReportRenderingIntegrityV1.ps1'
    target = 'scripts\Repair-DryRunReportRenderingIntegrityV1.ps1'
    label = 'Add dry-run report rendering repair tool'
  },
  @{
    source = 'scripts\Test-DryRunReportRenderingIntegrityClosureV1.ps1'
    target = 'scripts\Test-DryRunReportRenderingIntegrityClosureV1.ps1'
    label = 'Add dry-run report rendering integrity test'
  },
  @{
    source = 'README_AR.md'
    target = 'README_DRY_RUN_REPORT_RENDERING_INTEGRITY_CLOSURE_V1_AR.md'
    label = 'Add report rendering closure readme'
  },
  @{
    source = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'
    target = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'
    label = 'Update report rendering root-cause record'
  },
  @{
    source = 'MANIFEST.md'
    target = 'MANIFEST_DRY_RUN_REPORT_RENDERING_INTEGRITY_CLOSURE_V1.md'
    label = 'Add report rendering closure manifest'
  }
)

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\dry_run_report_rendering_integrity_$stamp"
$backupRunnerPath = Join-Path $backupRoot 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'

if ($PSCmdlet.ShouldProcess((Split-Path -Parent $backupRunnerPath), 'Create runner backup directory when needed')) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $backupRunnerPath) -Force | Out-Null
}

if ($PSCmdlet.ShouldProcess($backupRunnerPath, 'Backup current read-only runner before targeted repair')) {
  Copy-Item -LiteralPath $runnerTarget -Destination $backupRunnerPath -Force
}

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if (-not (Test-Path -LiteralPath $source)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$source"
  }

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, $entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

$repairPath = Join-Path $Target 'scripts\Repair-DryRunReportRenderingIntegrityV1.ps1'

if ($WhatIfPreference) {
  'REPAIR_STATUS=WHATIF_NOT_EXECUTED'
}
else {
  & $repairPath -ProjectRoot $Target
}

"INSTALL_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count)"
"BACKUP_PATH=$backupRoot"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'NEXT_STEP=RUN_REPORT_RENDERING_STATIC_TEST_AND_DRY_RUN_ONLY'
