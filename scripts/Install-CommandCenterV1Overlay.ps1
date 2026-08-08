[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$target = (Resolve-Path -LiteralPath $ProjectRoot).Path
$items = @('command_center','tests','README_COMMAND_CENTER_V1_AR.md','COMMAND_CENTER_V1_SECURITY_CONTRACT.md','COMMAND_CENTER_V1_UAT.md','CHANGELOG_COMMAND_CENTER_V1.md','integration_example.py','scripts/Test-CommandCenterV1Static.ps1')
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backup = Join-Path $target "backups/command_center_v1_$stamp"

foreach ($item in $items) {
  $source = Join-Path $package $item
  if (-not (Test-Path -LiteralPath $source)) { throw "PACKAGE_ITEM_MISSING=$source" }
}

if ($PSCmdlet.ShouldProcess($backup, 'Create command center preimage backup')) {
  New-Item -ItemType Directory -Path $backup -Force | Out-Null
}

foreach ($item in $items) {
  $source = Join-Path $package $item
  $destination = Join-Path $target $item
  if (Test-Path -LiteralPath $destination) {
    $backupDest = Join-Path $backup $item
    $parent = Split-Path -Parent $backupDest
    if ($PSCmdlet.ShouldProcess($backupDest, 'Backup existing Command Center target')) { New-Item -ItemType Directory -Path $parent -Force | Out-Null; Copy-Item -LiteralPath $destination -Destination $backupDest -Recurse -Force }
  }
  if ($PSCmdlet.ShouldProcess($destination, 'Install Command Center overlay')) {
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
  }
}

if ($WhatIfPreference) {
  'INSTALL_STATUS=WHATIF_COMPLETE'
  'PROJECT_MUTATION=NONE'
} else {
  'INSTALL_STATUS=COMPLETE'
  "BACKUP_PATH=$backup"
  'CORE_RUNTIME_MUTATION=NONE'
  'CORE_11_LINE_CONTRACT_MUTATION=NONE'
  'MODEL_EXECUTION=NONE'
  'PILOT_EXECUTION=NOT_EXECUTED'
  'PLATFORM_MUTATION=NONE'
  'DATABASE_ACCESS=NONE'
  'GIT_WRITE=NONE'
  'DEPLOYMENT=NONE'
  'SECRETS_ACCESS=NONE'
  'MEMORY_WRITE=NONE'
  'NEXT_STEP=ADD_EXPLICIT_MOUNT_CALL_TO_EXISTING_FASTAPI_ENTRYPOINT_ONLY'
}
