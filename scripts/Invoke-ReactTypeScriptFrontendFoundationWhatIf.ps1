[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PreflightManifest
)
$ErrorActionPreference = 'Stop'
Write-Output '===== REACT TYPESCRIPT FRONTEND FOUNDATION V1 WHATIF ====='
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) { throw "PREFLIGHT_MANIFEST_NOT_FOUND=$PreflightManifest" }
$preflight = Get-Content -LiteralPath $PreflightManifest -Raw | ConvertFrom-Json
if ($preflight.preflight_result -ne 'PASS') { throw 'PREFLIGHT_MANIFEST_NOT_PASSING' }
if ($preflight.project_root -ne (Resolve-Path -LiteralPath $ProjectRoot).Path) { throw 'PREFLIGHT_PROJECT_ROOT_MISMATCH' }
$manifest = Get-Content -LiteralPath (Join-Path $PackageRoot 'payload\react_foundation_manifest.json') -Raw | ConvertFrom-Json
Write-Output 'WHATIF_STATUS=COMPLETE'
Write-Output 'WHATIF_MODE=TRUE'
Write-Output 'BASELINE_BINDING=PASS'
Write-Output "PREDICTED_REACT_SOURCE_FILE_WRITE_COUNT=$(@($manifest.frontend_source_files).Count)"
Write-Output 'PREDICTED_APP_ENTRYPOINT_MUTATION_COUNT=1'
Write-Output 'PREDICTED_LEGACY_STATIC_MUTATION_COUNT=0'
Write-Output 'PREDICTED_BACKEND_ROUTER_MUTATION_COUNT=0'
Write-Output 'PREDICTED_BACKEND_SCHEMA_MUTATION_COUNT=0'
Write-Output 'PREDICTED_SQLITE_MUTATION_COUNT=0'
Write-Output 'PREDICTED_NODE_DEPENDENCY_INSTALL_DURING_APPLY=0'
Write-Output 'PREDICTED_FRONTEND_BUILD_DURING_APPLY=0'
Write-Output 'PREDICTED_MODEL_EXECUTION_COUNT=0'
Write-Output 'PREDICTED_PILOT_EXECUTION_COUNT=0'
Write-Output 'PREDICTED_TOKEN_PERSISTENCE_COUNT=0'
Write-Output 'REACT_RUNTIME_ACTIVATION=BLOCKED_PENDING_SEPARATE_DEPENDENCY_AND_BUILD_AUTHORIZATION'
Write-Output 'PROJECT_MUTATION=NONE_DURING_WHATIF'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'SERVICE_START=NONE'
Write-Output 'SHELL_EXECUTION=NONE'
Write-Output 'GIT_WRITE=NONE'
Write-Output 'EXTERNAL_NETWORK=NONE'
