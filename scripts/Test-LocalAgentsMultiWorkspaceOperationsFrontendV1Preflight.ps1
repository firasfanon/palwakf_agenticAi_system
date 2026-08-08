[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$PackageRoot,
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$ProjectRoot
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

Write-Output "===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 PREFLIGHT ====="

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw ("PROJECT_ROOT_NOT_FOUND=" + $ProjectRoot)
}

$bindingPath = Join-Path $PackageRoot "baseline_binding.json"
if (-not (Test-Path -LiteralPath $bindingPath -PathType Leaf)) {
  throw ("BASELINE_BINDING_NOT_FOUND=" + $bindingPath)
}
$binding = Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json

$assetResults = @()
$failureCount = 0
$preimageCount = 0
$postimageCount = 0

foreach ($asset in @($binding.assets)) {
  $relativePath = [string]$asset.relative_path
  $targetPath = Join-Path $ProjectRoot (Convert-RelativePath -Value $relativePath)
  $payloadPath = Join-Path $PackageRoot ("payload\" + $relativePath)

  if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
    Write-Output ("PREFLIGHT_ASSET_STATE=" + $relativePath + "=MISSING")
    $failureCount++
    continue
  }
  if (-not (Test-Path -LiteralPath $payloadPath -PathType Leaf)) {
    Write-Output ("PREFLIGHT_PAYLOAD_STATE=" + $relativePath + "=MISSING")
    $failureCount++
    continue
  }

  $actualHash = Get-Sha256 -Path $targetPath
  $payloadHash = Get-Sha256 -Path $payloadPath
  if ($payloadHash -ne [string]$asset.postimage_sha256) {
    Write-Output ("PREFLIGHT_PAYLOAD_HASH=" + $relativePath + "=MISMATCH")
    $failureCount++
    continue
  }

  $state = ""
  if ($actualHash -eq [string]$asset.preimage_sha256) {
    $state = "PREIMAGE_EXPECTED"
    $preimageCount++
  }
  elseif ($actualHash -eq [string]$asset.postimage_sha256) {
    $state = "EXACT_POSTIMAGE_PRESENT"
    $postimageCount++
  }
  else {
    $state = "DRIFT_DETECTED"
    $failureCount++
  }

  Write-Output ("PREFLIGHT_ASSET_STATE=" + $relativePath + "=" + $state)
  $assetResults += [pscustomobject]@{
    relative_path = $relativePath
    target_path = $targetPath
    preimage_sha256 = [string]$asset.preimage_sha256
    postimage_sha256 = [string]$asset.postimage_sha256
    actual_sha256 = $actualHash
    state = $state
  }
}

$manifestRoot = Join-Path $env:TEMP ("local_agents_frontend_v1_preflight_" + (Get-Date -Format "yyyyMMdd_HHmmssfff"))
New-Item -ItemType Directory -Path $manifestRoot -Force | Out-Null
$manifestPath = Join-Path $manifestRoot "preflight_manifest.json"
$manifest = [pscustomobject]@{
  contract = "LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_PREFLIGHT"
  generated_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot
  package_root = $PackageRoot
  failure_count = $failureCount
  preimage_asset_count = $preimageCount
  exact_postimage_asset_count = $postimageCount
  assets = $assetResults
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Output ("PREFLIGHT_MANIFEST=" + $manifestPath)
Write-Output ("PREFLIGHT_FAILURE_COUNT=" + $failureCount)
Write-Output "PREFLIGHT_SCOPE=STATIC_FRONTEND_ASSETS_ONLY"
Write-Output "PREFLIGHT_BACKEND_ROUTER_MUTATION=NONE"
Write-Output "PREFLIGHT_BACKEND_SCHEMA_MUTATION=NONE"
Write-Output "PREFLIGHT_FRONTEND_WRITE_REQUESTS=NONE"
Write-Output "PREFLIGHT_NO_TOKEN_PERSISTENCE=REQUIRED"
Write-Output "PROJECT_MUTATION=NONE"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "SERVICE_START=NONE"
Write-Output "SHELL_EXECUTION=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "EXTERNAL_NETWORK=NONE"

if ($failureCount -ne 0) {
  throw "PREFLIGHT_RESULT=FAIL"
}

Write-Output "PREFLIGHT_RESULT=PASS"
