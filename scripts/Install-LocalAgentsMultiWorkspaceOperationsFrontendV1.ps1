[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$PackageRoot,
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$ProjectRoot,
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$PreflightManifest,
  [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Get-Sha256 {
  param([Parameter(Mandatory = $true)][string]$Path)
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Convert-RelativePath {
  param([Parameter(Mandatory = $true)][string]$Value)
  return $Value.Replace("\", [string][System.IO.Path]::DirectorySeparatorChar)
}

if (-not $Apply) {
  throw "APPLY_SWITCH_REQUIRED"
}
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) {
  throw ("PREFLIGHT_MANIFEST_NOT_FOUND=" + $PreflightManifest)
}

$preflight = Get-Content -LiteralPath $PreflightManifest -Raw | ConvertFrom-Json
if ([string]$preflight.project_root -ne $ProjectRoot) {
  throw "PREFLIGHT_PROJECT_ROOT_MISMATCH"
}
if ([int]$preflight.failure_count -ne 0) {
  throw "PREFLIGHT_NOT_GREEN"
}

$binding = Get-Content -LiteralPath (Join-Path $PackageRoot "baseline_binding.json") -Raw | ConvertFrom-Json
$backupRoot = Join-Path $ProjectRoot ("backups\local_agents_multi_workspace_operations_frontend_v1_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

$replacedCount = 0
$noopCount = 0
foreach ($asset in @($binding.assets)) {
  $relativePath = [string]$asset.relative_path
  $targetPath = Join-Path $ProjectRoot (Convert-RelativePath -Value $relativePath)
  $payloadPath = Join-Path $PackageRoot ("payload\" + $relativePath)
  $currentHash = Get-Sha256 -Path $targetPath

  if ($currentHash -eq [string]$asset.postimage_sha256) {
    $noopCount++
    continue
  }
  if ($currentHash -ne [string]$asset.preimage_sha256) {
    throw ("APPLY_DRIFT_DETECTED=" + $relativePath)
  }

  $backupPath = Join-Path $backupRoot (Convert-RelativePath -Value $relativePath)
  $backupParent = Split-Path -Parent $backupPath
  New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
  Copy-Item -LiteralPath $targetPath -Destination $backupPath -Force
  Copy-Item -LiteralPath $payloadPath -Destination $targetPath -Force

  $postHash = Get-Sha256 -Path $targetPath
  if ($postHash -ne [string]$asset.postimage_sha256) {
    throw ("APPLY_POSTIMAGE_HASH_MISMATCH=" + $relativePath)
  }
  $replacedCount++
}

Write-Output "INSTALL_STATUS=COMPLETE"
Write-Output ("BACKUP_PATH=" + $backupRoot)
Write-Output ("STATIC_ASSET_REPLACEMENT_COUNT=" + $replacedCount)
Write-Output ("STATIC_ASSET_NOOP_COUNT=" + $noopCount)
Write-Output "BACKEND_ROUTER_MUTATION=NONE"
Write-Output "BACKEND_SCHEMA_MUTATION=NONE"
Write-Output "FRONTEND_WRITE_REQUESTS=NONE"
Write-Output "TOKEN_PERSISTENCE=NONE"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "SERVICE_START=NONE"
Write-Output "SHELL_EXECUTION=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "DEPLOYMENT=NONE"
Write-Output "EXTERNAL_NETWORK=NONE"
