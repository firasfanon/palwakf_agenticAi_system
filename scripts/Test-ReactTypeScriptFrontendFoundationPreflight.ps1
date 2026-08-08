[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Require-File([string]$Path) { if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "REQUIRED_FILE_NOT_FOUND=$Path" } }
Write-Output '===== REACT TYPESCRIPT FRONTEND FOUNDATION V1 PREFLIGHT ====='
$projectFull = (Resolve-Path -LiteralPath $ProjectRoot).Path
$manifestPath = Join-Path $PackageRoot 'payload\react_foundation_manifest.json'
Require-File $manifestPath
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$appPath = Join-Path $projectFull $manifest.app_entrypoint.relative_path.Replace('/', '\')
Require-File $appPath
$appHash = Get-Sha256 $appPath
$appState = ''
if ($appHash -eq $manifest.app_entrypoint.preimage_sha256) { $appState = 'PREIMAGE_EXPECTED' }
elseif ($appHash -eq $manifest.app_entrypoint.postimage_sha256) { $appState = 'EXACT_POSTIMAGE_PRESENT' }
else { throw "APP_ENTRYPOINT_DRIFT=$appHash" }
Write-Output "PREFLIGHT_APP_ENTRYPOINT_STATE=$appState"
foreach ($legacy in @($manifest.legacy_static_fallback)) {
  $legacyPath = Join-Path $projectFull $legacy.relative_path.Replace('/', '\')
  Require-File $legacyPath
  $legacyHash = Get-Sha256 $legacyPath
  if ($legacyHash -ne $legacy.sha256) { throw "LEGACY_STATIC_DRIFT=$($legacy.relative_path):$legacyHash" }
}
Write-Output 'PREFLIGHT_LEGACY_STATIC_FALLBACK=EXACT_POSTIMAGE_PRESENT'
$frontendRoot = Join-Path $projectFull 'frontend'
$frontendState = 'PREIMAGE_EXPECTED_ABSENT'
if (Test-Path -LiteralPath $frontendRoot -PathType Container) {
  $marker = Join-Path $frontendRoot '.local_agents_react_foundation.json'
  if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) { throw 'FRONTEND_ROOT_EXISTS_WITHOUT_REACT_FOUNDATION_MARKER' }
  foreach ($entry in @($manifest.frontend_source_files)) {
    $relative = $entry.relative_path.Substring('frontend/'.Length).Replace('/', '\')
    $path = Join-Path $frontendRoot $relative
    Require-File $path
    if ((Get-Sha256 $path) -ne $entry.sha256) { throw "REACT_FRONTEND_SOURCE_DRIFT=$relative" }
  }
  $frontendState = 'EXACT_POSTIMAGE_PRESENT'
}
Write-Output "PREFLIGHT_REACT_FRONTEND_STATE=$frontendState"
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($null -eq $node -or $null -eq $npm) { throw 'NODE_AND_NPM_REQUIRED_FOR_FUTURE_SEPARATE_BUILD_GATE' }
Write-Output "NODE_VERSION=$(& node --version)"
Write-Output "NPM_VERSION=$(& npm --version)"
$tempRoot = Join-Path $env:TEMP ('react_foundation_preflight_' + (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$reportPath = Join-Path $tempRoot 'preflight_manifest.json'
$report = [pscustomobject]@{
  contract = 'LOCAL_AGENTS_REACT_TYPESCRIPT_FRONTEND_FOUNDATION_V1_PREFLIGHT'
  package_root = (Resolve-Path -LiteralPath $PackageRoot).Path
  project_root = $projectFull
  app_entrypoint_state = $appState
  react_frontend_state = $frontendState
  frontend_source_file_count = @($manifest.frontend_source_files).Count
  legacy_static_file_count = @($manifest.legacy_static_fallback).Count
  external_network = 'NONE'
  dependency_install_during_apply = 'NONE'
  build_during_apply = 'NONE'
  preflight_result = 'PASS'
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Output "PREFLIGHT_MANIFEST=$reportPath"
Write-Output 'PREFLIGHT_FAILURE_COUNT=0'
Write-Output 'PREFLIGHT_SCOPE=REACT_SOURCE_AND_CONDITIONAL_APP_MOUNT_ONLY'
Write-Output 'PREFLIGHT_BACKEND_ROUTER_MUTATION=NONE'
Write-Output 'PREFLIGHT_BACKEND_SCHEMA_MUTATION=NONE'
Write-Output 'PREFLIGHT_LEGACY_STATIC_MUTATION=NONE'
Write-Output 'PROJECT_MUTATION=NONE'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'SERVICE_START=NONE'
Write-Output 'SHELL_EXECUTION=NONE'
Write-Output 'GIT_WRITE=NONE'
Write-Output 'EXTERNAL_NETWORK=NONE'
Write-Output 'PREFLIGHT_RESULT=PASS'
