[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,

  [Parameter(Mandatory = $true)]
  [string]$BackupPath
)

$ErrorActionPreference = 'Stop'
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)
$Backup = [System.IO.Path]::GetFullPath($BackupPath)

if (-not (Test-Path -LiteralPath $Backup)) {
  throw "BACKUP_PATH_NOT_FOUND=$Backup"
}

$relativePaths = @(
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Test-ExactOutputBoundaryTrailingTextClosureV1.ps1',
  'scripts\Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1',
  'scripts\Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1',
  'ROOT_CAUSE_AND_REMEDIATION_AR.md'
)

$restoredCount = 0

foreach ($relative in $relativePaths) {
  $source = Join-Path $Backup $relative
  $destination = Join-Path $Target $relative

  if (-not (Test-Path -LiteralPath $source)) {
    continue
  }

  $destinationDirectory = Split-Path -Parent $destination

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create rollback target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, "Restore backup file $relative")) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
    $restoredCount++
  }
}

"ROLLBACK_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"RESTORED_FILE_COUNT=$restoredCount"
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
