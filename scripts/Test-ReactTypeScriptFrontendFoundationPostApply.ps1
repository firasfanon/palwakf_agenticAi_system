[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Require-File([string]$Path) { if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "REQUIRED_FILE_NOT_FOUND=$Path" } }
Write-Output '===== REACT TYPESCRIPT FRONTEND FOUNDATION V1 POST-APPLY ====='
$projectFull = (Resolve-Path -LiteralPath $ProjectRoot).Path
$manifest = Get-Content -LiteralPath (Join-Path $PackageRoot 'payload\react_foundation_manifest.json') -Raw | ConvertFrom-Json
$appPath = Join-Path $projectFull $manifest.app_entrypoint.relative_path.Replace('/', '\')
Require-File $appPath
if ((Get-Sha256 $appPath) -ne $manifest.app_entrypoint.postimage_sha256) { throw 'POST_APPLY_APP_ENTRYPOINT_CONTRACT_FAILED' }
$frontendRoot = Join-Path $projectFull 'frontend'
foreach ($entry in @($manifest.frontend_source_files)) {
  $relative = $entry.relative_path.Substring('frontend/'.Length).Replace('/', '\')
  $path = Join-Path $frontendRoot $relative
  Require-File $path
  if ((Get-Sha256 $path) -ne $entry.sha256) { throw "POST_APPLY_REACT_SOURCE_CONTRACT_FAILED=$relative" }
}
foreach ($legacy in @($manifest.legacy_static_fallback)) {
  $legacyPath = Join-Path $projectFull $legacy.relative_path.Replace('/', '\')
  Require-File $legacyPath
  if ((Get-Sha256 $legacyPath) -ne $legacy.sha256) { throw "POST_APPLY_LEGACY_FALLBACK_CONTRACT_FAILED=$($legacy.relative_path)" }
}
$forbidden = @('localStorage', 'sessionStorage', 'Authorization', 'Bearer ', 'method: "POST"', "method: 'POST'", 'method: "PUT"', "method: 'PUT'", 'method: "PATCH"', "method: 'PATCH'", 'method: "DELETE"', "method: 'DELETE'")
foreach ($needle in $forbidden) {
  $hits = Select-String -LiteralPath (Get-ChildItem -LiteralPath $frontendRoot -Recurse -File | Select-Object -ExpandProperty FullName) -SimpleMatch -Pattern $needle -ErrorAction SilentlyContinue
  if ($null -ne $hits) { throw "POST_APPLY_FORBIDDEN_FRONTEND_PATTERN=$needle" }
}
$tempRoot = Join-Path $env:TEMP ('react_foundation_post_apply_' + (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$reportPath = Join-Path $tempRoot 'post_apply_report.json'
$report = [pscustomobject]@{
  contract = 'LOCAL_AGENTS_REACT_TYPESCRIPT_FRONTEND_FOUNDATION_V1_POST_APPLY'
  app_entrypoint = 'PASS'
  react_source_contract = 'PASS'
  legacy_fallback = 'PASS'
  token_persistence = 'NONE'
  write_requests = 'NONE'
  dependency_install = 'NOT_EXECUTED'
  frontend_build = 'NOT_EXECUTED'
  runtime_activation = 'PENDING_SEPARATE_AUTHORIZATION'
  model_execution = 'NONE'
  pilot_execution = 'NOT_EXECUTED'
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
$archivePath = Join-Path $env:TEMP ('react_foundation_post_apply_' + (Get-Date -Format 'yyyyMMdd_HHmmssfff') + '.zip')
Compress-Archive -LiteralPath $reportPath -DestinationPath $archivePath -Force
Write-Output 'POST_APPLY_REACT_SOURCE_CONTRACT=PASS'
Write-Output 'POST_APPLY_APP_ENTRYPOINT_CONTRACT=PASS'
Write-Output 'POST_APPLY_LEGACY_FALLBACK_PRESERVATION=PASS'
Write-Output 'POST_APPLY_NO_TOKEN_PERSISTENCE=PASS'
Write-Output 'POST_APPLY_READ_ONLY_GET_CLIENT_GUARD=PASS'
Write-Output "EVIDENCE_ARCHIVE=$archivePath"
Write-Output 'REACT_RUNTIME_ACTIVATION=PENDING_SEPARATE_DEPENDENCY_RESOLUTION_AND_BUILD_AUTHORIZATION'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'PROJECT_MUTATION=NONE_DURING_UAT'
