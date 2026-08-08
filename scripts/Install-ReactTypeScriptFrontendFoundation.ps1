[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PreflightManifest,
  [switch]$Apply
)
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Require-File([string]$Path) { if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "REQUIRED_FILE_NOT_FOUND=$Path" } }
if (-not $Apply) { throw 'APPLY_SWITCH_REQUIRED' }
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) { throw "PREFLIGHT_MANIFEST_NOT_FOUND=$PreflightManifest" }
$preflight = Get-Content -LiteralPath $PreflightManifest -Raw | ConvertFrom-Json
$projectFull = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ($preflight.preflight_result -ne 'PASS' -or $preflight.project_root -ne $projectFull) { throw 'PREFLIGHT_BINDING_INVALID' }
$manifest = Get-Content -LiteralPath (Join-Path $PackageRoot 'payload\react_foundation_manifest.json') -Raw | ConvertFrom-Json
$appPath = Join-Path $projectFull $manifest.app_entrypoint.relative_path.Replace('/', '\')
Require-File $appPath
$appHash = Get-Sha256 $appPath
if ($appHash -ne $manifest.app_entrypoint.preimage_sha256 -and $appHash -ne $manifest.app_entrypoint.postimage_sha256) { throw "APP_ENTRYPOINT_DRIFT_BEFORE_APPLY=$appHash" }
$backupRoot = Join-Path $projectFull ('backups\react_typescript_frontend_foundation_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
Copy-Item -LiteralPath $appPath -Destination (Join-Path $backupRoot 'app.py.preapply') -Force
$frontendRoot = Join-Path $projectFull 'frontend'
if (Test-Path -LiteralPath $frontendRoot -PathType Container) { Copy-Item -LiteralPath $frontendRoot -Destination (Join-Path $backupRoot 'frontend.preapply') -Recurse -Force }
$sourceFrontend = Join-Path $PackageRoot 'payload\frontend'
foreach ($file in (Get-ChildItem -LiteralPath $sourceFrontend -Recurse -File)) {
  $relative = $file.FullName.Substring($sourceFrontend.Length).TrimStart('\')
  $destination = Join-Path $frontendRoot $relative
  $parent = Split-Path -Parent $destination
  New-Item -ItemType Directory -Path $parent -Force | Out-Null
  Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
}
$sourceApp = Join-Path $PackageRoot 'payload\backend\src\palwakf_local_agents\app.py'
if ((Get-Sha256 $appPath) -ne $manifest.app_entrypoint.postimage_sha256) { Copy-Item -LiteralPath $sourceApp -Destination $appPath -Force }
foreach ($entry in @($manifest.frontend_source_files)) {
  $relative = $entry.relative_path.Substring('frontend/'.Length).Replace('/', '\')
  $path = Join-Path $frontendRoot $relative
  Require-File $path
  if ((Get-Sha256 $path) -ne $entry.sha256) { throw "REACT_FRONTEND_POSTIMAGE_VERIFICATION_FAILED=$relative" }
}
if ((Get-Sha256 $appPath) -ne $manifest.app_entrypoint.postimage_sha256) { throw 'APP_ENTRYPOINT_POSTIMAGE_VERIFICATION_FAILED' }
Write-Output '===== REACT TYPESCRIPT FRONTEND FOUNDATION V1 APPLY ====='
Write-Output 'INSTALL_STATUS=COMPLETE'
Write-Output "BACKUP_PATH=$backupRoot"
Write-Output "REACT_SOURCE_FILE_WRITE_COUNT=$(@($manifest.frontend_source_files).Count)"
Write-Output 'APP_ENTRYPOINT_MUTATION=CONDITIONAL_REACT_DIST_MOUNT_APPLIED'
Write-Output 'LEGACY_STATIC_MUTATION=NONE'
Write-Output 'NODE_DEPENDENCY_INSTALL_DURING_APPLY=NONE'
Write-Output 'FRONTEND_BUILD_DURING_APPLY=NONE'
Write-Output 'REACT_RUNTIME_ACTIVATION=PENDING_SEPARATE_DEPENDENCY_RESOLUTION_AND_BUILD_AUTHORIZATION'
Write-Output 'BACKEND_ROUTER_MUTATION=NONE'
Write-Output 'BACKEND_SCHEMA_MUTATION=NONE'
Write-Output 'SQLITE_MUTATION=NONE'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'SERVICE_START=NONE'
Write-Output 'SHELL_EXECUTION=NONE'
Write-Output 'GIT_WRITE=NONE'
Write-Output 'EXTERNAL_NETWORK=NONE'
