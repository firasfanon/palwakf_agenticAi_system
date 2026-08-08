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

$registrySource = Join-Path $Backup 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'
$registryTarget = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if (-not (Test-Path -LiteralPath $registrySource)) {
  throw "REGISTRY_BACKUP_NOT_FOUND=$registrySource"
}

if ($PSCmdlet.ShouldProcess($registryTarget, 'Restore Pack 01 registry backup')) {
  Copy-Item -LiteralPath $registrySource -Destination $registryTarget -Force
}

"ROLLBACK_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"RESTORED_REGISTRY_PATH=$registryTarget"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
