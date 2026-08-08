[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,

  [Parameter(Mandatory = $true)]
  [string]$BackupPath
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$Backup = [System.IO.Path]::GetFullPath($BackupPath)

$source = Join-Path $Backup 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
$target = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if (-not (Test-Path -LiteralPath $source)) {
  throw "REGISTRY_BACKUP_NOT_FOUND=$source"
}

if ($PSCmdlet.ShouldProcess($target, 'Restore registry backup from before Pack 01 V1.2 bootstrap')) {
  Copy-Item -LiteralPath $source -Destination $target -Force
}

"ROLLBACK_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"RESTORED_REGISTRY_PATH=$target"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
