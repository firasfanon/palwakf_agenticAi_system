[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot,
  [ValidateSet("Upgrade")][string]$Mode="Upgrade"
)
$ErrorActionPreference = "Stop"
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
$sourceRoot = Join-Path $package "static"
$targetRoot = Join-Path $project "backend\src\palwakf_local_agents\command_center\static"
$relativeFiles = @("index.html","styles.css","app.js")

foreach ($rel in $relativeFiles) {
  foreach ($path in @((Join-Path $sourceRoot $rel),(Join-Path $targetRoot $rel))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      throw "REQUIRED_STATIC_FILE_NOT_FOUND=$path"
    }
  }
}

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$backupRoot = Join-Path $project "backups\command_center_operational_ui_ux_read_only_v1_revb_$timestamp"
$manifestPath = Join-Path $backupRoot "install_preimage_manifest.json"

if ($WhatIfPreference) {
  foreach ($rel in $relativeFiles) {
    $target = Join-Path $targetRoot $rel
    $backup = Join-Path $backupRoot (Join-Path "preimage\static" $rel)
    if ($PSCmdlet.ShouldProcess($backup, "Backup current Command Center static asset")) {
      Copy-Item -LiteralPath $target -Destination $backup -Force
    }
    if ($PSCmdlet.ShouldProcess($target, "Install read-only operational UI asset")) {
      Copy-Item -LiteralPath (Join-Path $sourceRoot $rel) -Destination $target -Force
    }
  }
  Write-Output "INSTALL_STATUS=WHATIF_COMPLETE"
  Write-Output "INSTALL_MODE=$Mode"
  Write-Output "BACKUP_PATH=$backupRoot"
  Write-Output "BACKUP_MANIFEST_PATH=$manifestPath"
  Write-Output "BACKUP_STATUS=PLANNED"
  Write-Output "INSTALL_BACKUP_STRATEGY=EXACT_STATIC_ASSET_PREIMAGE_COPY"
  Write-Output "UI_MUTATION_SCOPE=STATIC_ASSETS_ONLY"
  Write-Output "STATIC_ASSET_COUNT=3"
  Write-Output "SCRIPT_ENCODING_GATE=ASCII_MARKERS_ONLY"
  Write-Output "RESPONSIVE_EVAL_REGEX=WHITESPACE_TOLERANT"
  Write-Output "APP_ENTRYPOINT_MUTATION=NONE"
  Write-Output "ROUTER_MUTATION=NONE"
  Write-Output "STORE_MUTATION=NONE"
  Write-Output "API_MUTATION=NONE"
  Write-Output "MODEL_EXECUTION=NONE"
  Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
  Write-Output "PROJECT_MUTATION=PLANNED_STATIC_ASSETS_ONLY"
  exit 0
}

New-Item -ItemType Directory -Path (Join-Path $backupRoot "preimage\static") -Force | Out-Null
$preimages = @()
foreach ($rel in $relativeFiles) {
  $source = Join-Path $sourceRoot $rel
  $target = Join-Path $targetRoot $rel
  $backup = Join-Path $backupRoot (Join-Path "preimage\static" $rel)
  Copy-Item -LiteralPath $target -Destination $backup -Force
  $preimages += [ordered]@{
    relative_path = "static/$rel"
    source_sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    preimage_sha256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  }
}

$manifest = [ordered]@{
  package_id = "MEGA_BATCH_COMMAND_CENTER_OPERATIONAL_UI_UX_READ_ONLY_V1_REVB"
  created_at_local = (Get-Date).ToString("o")
  install_mode = $Mode
  patch_scope = "STATIC_ASSETS_ONLY"
  script_encoding_gate = "ASCII_MARKERS_ONLY"
  responsive_eval_regex = "WHITESPACE_TOLERANT"
  assets = $preimages
  app_entrypoint_mutation = "NONE"
  router_mutation = "NONE"
  store_mutation = "NONE"
  api_mutation = "NONE"
  model_execution = "NONE"
  pilot_execution = "NOT_EXECUTED"
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

$installed = @()
foreach ($rel in $relativeFiles) {
  $source = Join-Path $sourceRoot $rel
  $target = Join-Path $targetRoot $rel
  Copy-Item -LiteralPath $source -Destination $target -Force
  $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
  $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if ($sourceHash -ne $targetHash) {
    throw "STATIC_ASSET_INSTALL_HASH_MISMATCH=$rel"
  }
  $installed += "$rel=$targetHash"
}

Write-Output "INSTALL_STATUS=COMPLETE"
Write-Output "INSTALL_MODE=$Mode"
Write-Output "BACKUP_PATH=$backupRoot"
Write-Output "BACKUP_MANIFEST_PATH=$manifestPath"
Write-Output "BACKUP_STATUS=COMPLETE"
Write-Output "INSTALL_BACKUP_STRATEGY=EXACT_STATIC_ASSET_PREIMAGE_COPY"
Write-Output "STATIC_ASSET_HASHES=$($installed -join ';')"
Write-Output "UI_MUTATION_SCOPE=STATIC_ASSETS_ONLY"
Write-Output "STATIC_ASSET_COUNT=3"
Write-Output "SCRIPT_ENCODING_GATE=ASCII_MARKERS_ONLY"
Write-Output "RESPONSIVE_EVAL_REGEX=WHITESPACE_TOLERANT"
Write-Output "APP_ENTRYPOINT_MUTATION=NONE"
Write-Output "ROUTER_MUTATION=NONE"
Write-Output "STORE_MUTATION=NONE"
Write-Output "API_MUTATION=NONE"
Write-Output "TASK_STATE_MUTATION=NONE"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "PLATFORM_MUTATION=NONE"
Write-Output "DATABASE_ACCESS=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "DEPLOYMENT=NONE"
Write-Output "SECRETS_ACCESS=NONE"
Write-Output "MEMORY_WRITE=NONE"
Write-Output "PROJECT_MUTATION=STATIC_ASSETS_ONLY"
Write-Output "NEXT_STEP=RUN_STATIC_GATE_UNITTEST_ROUTE_PROBE_AND_BROWSER_UAT"
exit 0
