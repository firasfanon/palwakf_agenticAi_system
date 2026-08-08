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
$source = Join-Path $Backup 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'
$destination = Join-Path $Target 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'

if (-not (Test-Path -LiteralPath $source)) {
  throw "RUNNER_BACKUP_NOT_FOUND=$source"
}

if ($PSCmdlet.ShouldProcess($destination, 'Restore read-only runner from dry-run rendering backup')) {
  Copy-Item -LiteralPath $source -Destination $destination -Force
}

"ROLLBACK_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"RESTORED_PATH=$destination"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
