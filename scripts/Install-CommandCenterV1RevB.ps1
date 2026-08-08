[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [ValidateSet('Upgrade')][string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path

function Write-Utf8NoBom {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Content
  )
  $parent = Split-Path -Parent $Path
  if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Get-Sha256OrEmpty {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (Test-Path -LiteralPath $Path -PathType Leaf) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
  }
  return ''
}

function Get-PatchedAppContent {
  param([Parameter(Mandatory = $true)][string]$AppPath)

  $lines = New-Object 'System.Collections.Generic.List[string]'
  [void]$lines.AddRange([string[]](Get-Content -LiteralPath $AppPath -Encoding UTF8))

  if ($lines -contains 'from .command_center import mount_command_center') {
    throw 'APP_ENTRYPOINT_ALREADY_HAS_COMMAND_CENTER_IMPORT'
  }
  if ($lines | Where-Object { $_ -match 'mount_command_center\(' }) {
    throw 'APP_ENTRYPOINT_ALREADY_HAS_COMMAND_CENTER_MOUNT'
  }

  if (-not ($lines -contains 'from pathlib import Path')) {
    $futureIndex = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
      if ($lines[$index] -eq 'from __future__ import annotations') {
        $futureIndex = $index
        break
      }
    }
    if ($futureIndex -lt 0) {
      throw 'APP_ENTRYPOINT_FUTURE_IMPORT_ANCHOR_NOT_FOUND'
    }
    $lines.Insert($futureIndex + 1, '')
    $lines.Insert($futureIndex + 2, 'from pathlib import Path')
  }

  $storeIndex = -1
  for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index] -eq 'from . import store') {
      $storeIndex = $index
      break
    }
  }
  if ($storeIndex -lt 0) {
    throw 'APP_ENTRYPOINT_STORE_IMPORT_ANCHOR_NOT_FOUND'
  }
  $lines.Insert($storeIndex + 1, 'from .command_center import mount_command_center')

  $appIndex = -1
  for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index] -match '^app\s*=\s*FastAPI\(') {
      $appIndex = $index
      break
    }
  }
  if ($appIndex -lt 0) {
    throw 'APP_ENTRYPOINT_FASTAPI_ANCHOR_NOT_FOUND'
  }

  $insert = @(
    '',
    'PROJECT_ROOT = Path(__file__).resolve().parents[3]',
    'mount_command_center(app, project_root=PROJECT_ROOT)',
    ''
  )
  for ($offset = $insert.Count - 1; $offset -ge 0; $offset--) {
    $lines.Insert($appIndex + 1, $insert[$offset])
  }

  return ([string]::Join("`r`n", $lines) + "`r`n")
}

$relativeFiles = @(
  'backend\src\palwakf_local_agents\command_center\__init__.py',
  'backend\src\palwakf_local_agents\command_center\models.py',
  'backend\src\palwakf_local_agents\command_center\read_only_store.py',
  'backend\src\palwakf_local_agents\command_center\router.py',
  'backend\src\palwakf_local_agents\command_center\static\index.html',
  'backend\src\palwakf_local_agents\command_center\static\styles.css',
  'backend\src\palwakf_local_agents\command_center\static\app.js',
  'backend\tests\test_command_center_read_only.py',
  'scripts\Test-CommandCenterV1RevBStatic.ps1',
  'README_COMMAND_CENTER_V1_1_REVB_AR.md',
  'COMMAND_CENTER_V1_1_REVB_SECURITY_CONTRACT.md',
  'COMMAND_CENTER_V1_1_REVB_UAT.md',
  'CHANGELOG_COMMAND_CENTER_V1_1_REVB.md'
)

$appRelative = 'backend\src\palwakf_local_agents\app.py'
foreach ($relative in $relativeFiles) {
  $source = Join-Path $package $relative
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw "PACKAGE_FILE_MISSING=$source"
  }
}
$appPath = Join-Path $project $appRelative
if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) {
  throw "PROJECT_APP_ENTRYPOINT_MISSING=$appPath"
}

$patchedApp = Get-PatchedAppContent -AppPath $appPath
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot = Join-Path $project "backups\command_center_v1_1_revb_$stamp"
$manifestPath = Join-Path $backupRoot 'install_preimage_manifest.json'
$plan = @($appRelative) + $relativeFiles

if ($PSCmdlet.ShouldProcess($backupRoot, 'Create Command Center Rev B preimage backup')) {
  New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
}

$preimages = @()
foreach ($relative in $plan) {
  $targetPath = Join-Path $project $relative
  $exists = Test-Path -LiteralPath $targetPath -PathType Leaf
  $backupRelative = if ($exists) { "preimage\$relative" } else { '' }
  $backupPath = if ($exists) { Join-Path $backupRoot $backupRelative } else { '' }

  if ($exists -and $PSCmdlet.ShouldProcess($backupPath, 'Backup existing Command Center Rev B target preimage')) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
    Copy-Item -LiteralPath $targetPath -Destination $backupPath -Force
  }

  $preimages += [ordered]@{
    relative_path = $relative
    existed_before = [bool]$exists
    sha256_before = if ($exists) { Get-Sha256OrEmpty -Path $targetPath } else { '' }
    backup_relative_path = $backupRelative
  }
}

$manifest = [ordered]@{
  package = 'LOCAL_AGENT_COMMAND_CENTER_V1_1_REVB'
  install_mode = $Mode
  created_at_local = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  project_root = $project
  backup_root = $backupRoot
  preimages = $preimages
  app_entrypoint_patch = 'EXPLICIT_MOUNT_ONLY'
  legacy_root_command_center_action = 'UNCHANGED'
  safety_posture = [ordered]@{
    MODEL_EXECUTION = 'NONE'
    PILOT_EXECUTION = 'NOT_EXECUTED'
    PLATFORM_MUTATION = 'NONE'
    DATABASE_ACCESS = 'NONE'
    GIT_WRITE = 'NONE'
    DEPLOYMENT = 'NONE'
    SECRETS_ACCESS = 'NONE'
    MEMORY_WRITE = 'NONE'
  }
}

if ($PSCmdlet.ShouldProcess($manifestPath, 'Write Command Center Rev B preimage manifest')) {
  Write-Utf8NoBom -Path $manifestPath -Content ($manifest | ConvertTo-Json -Depth 20)
}

if ($PSCmdlet.ShouldProcess($appPath, 'Patch FastAPI entrypoint with explicit Command Center mount')) {
  Write-Utf8NoBom -Path $appPath -Content $patchedApp
}

foreach ($relative in $relativeFiles) {
  $source = Join-Path $package $relative
  $destination = Join-Path $project $relative
  if ($PSCmdlet.ShouldProcess($destination, 'Install Command Center Rev B file')) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

if ($WhatIfPreference) {
  'INSTALL_STATUS=WHATIF_COMPLETE'
  "INSTALL_MODE=$Mode"
  "PLAN_ENTRY_COUNT=$($plan.Count)"
  "BACKUP_PATH=$backupRoot"
  "BACKUP_MANIFEST_PATH=$manifestPath"
  'BACKUP_STATUS=PLANNED'
  'INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY'
  'APP_ENTRYPOINT_MUTATION=PLANNED_EXPLICIT_MOUNT_ONLY'
  'LEGACY_ROOT_COMMAND_CENTER_ACTION=UNCHANGED'
  'PROJECT_MUTATION=NONE'
} else {
  $postinstall = @()
  foreach ($relative in $plan) {
    $targetPath = Join-Path $project $relative
    $postinstall += [ordered]@{
      relative_path = $relative
      sha256_after = Get-Sha256OrEmpty -Path $targetPath
    }
  }
  $manifest.postinstall = $postinstall
  $manifest.install_status = 'COMPLETE'
  $manifest.completed_at_local = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Write-Utf8NoBom -Path $manifestPath -Content ($manifest | ConvertTo-Json -Depth 20)

  'INSTALL_STATUS=COMPLETE'
  "INSTALL_MODE=$Mode"
  "PLAN_ENTRY_COUNT=$($plan.Count)"
  "BACKUP_PATH=$backupRoot"
  "BACKUP_MANIFEST_PATH=$manifestPath"
  'BACKUP_STATUS=COMPLETE'
  'INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY'
  'APP_ENTRYPOINT_MUTATION=EXPLICIT_MOUNT_ONLY'
  'LEGACY_ROOT_COMMAND_CENTER_ACTION=UNCHANGED'
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
  'NEXT_STEP=RUN_STATIC_AND_BACKEND_TESTS_ONLY'
}
