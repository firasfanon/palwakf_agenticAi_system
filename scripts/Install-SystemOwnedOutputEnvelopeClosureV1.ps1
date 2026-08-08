[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [ValidateSet('Upgrade')][string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path -LiteralPath $Target)) { throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target" }

$copyPlan = @(
  @{ source = 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'; target = 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'; label = 'Install merged evidence gateway and system-owned envelope runtime' },
  @{ source = 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'; target = 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'; label = 'Install V3 model-body contract' },
  @{ source = 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'; target = 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'; label = 'Install system-owned envelope runner' },
  @{ source = 'scripts\Test-SystemOwnedOutputEnvelopeClosureV1.ps1'; target = 'scripts\Test-SystemOwnedOutputEnvelopeClosureV1.ps1'; label = 'Add envelope static test' },
  @{ source = 'scripts\Invoke-SystemOwnedOutputEnvelopeEvalsV1.ps1'; target = 'scripts\Invoke-SystemOwnedOutputEnvelopeEvalsV1.ps1'; label = 'Add envelope deterministic evaluations' },
  @{ source = 'README_AR.md'; target = 'README_SYSTEM_OWNED_OUTPUT_ENVELOPE_CLOSURE_V1_AR.md'; label = 'Add closure readme' },
  @{ source = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'; target = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'; label = 'Update root-cause record' },
  @{ source = 'MANIFEST.md'; target = 'MANIFEST_SYSTEM_OWNED_OUTPUT_ENVELOPE_CLOSURE_V1.md'; label = 'Add closure manifest' }
)

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $Target "backups\system_owned_output_envelope_$stamp"

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if (-not (Test-Path -LiteralPath $source)) { throw "PACKAGE_SOURCE_NOT_FOUND=$source" }

  if (Test-Path -LiteralPath $destination) {
    $backupPath = Join-Path $backupRoot $entry.target

    if ($PSCmdlet.ShouldProcess((Split-Path -Parent $backupPath), 'Create rollback directory when needed')) {
      New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
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
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'NEXT_STEP=RUN_STATIC_AND_DETERMINISTIC_ENVELOPE_TESTS_ONLY'
