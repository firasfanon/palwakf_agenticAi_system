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

function Get-FrontendNoWriteGuardPatterns {
  return @(
    "localStorage",
    "sessionStorage",
    "Authorization",
    "/pilot/execute",
    'method\s*:\s*[''"]POST',
    '\.post\s*\('
  )
}

$binding = Get-Content -LiteralPath (Join-Path $PackageRoot "baseline_binding.json") -Raw | ConvertFrom-Json
$actualAssets = @()
foreach ($asset in @($binding.assets)) {
  $relativePath = [string]$asset.relative_path
  $targetPath = Join-Path $ProjectRoot (Convert-RelativePath -Value $relativePath)
  if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
    throw ("POST_APPLY_ASSET_MISSING=" + $relativePath)
  }
  $actualHash = Get-Sha256 -Path $targetPath
  if ($actualHash -ne [string]$asset.postimage_sha256) {
    throw ("POST_APPLY_HASH_MISMATCH=" + $relativePath)
  }
  $actualAssets += [pscustomobject]@{ relative_path = $relativePath; sha256 = $actualHash }
}

$allText = ""
foreach ($asset in @($binding.assets)) {
  $targetPath = Join-Path $ProjectRoot (Convert-RelativePath -Value ([string]$asset.relative_path))
  $allText += "`n" + [System.IO.File]::ReadAllText($targetPath)
}

$blockedPatterns = Get-FrontendNoWriteGuardPatterns
foreach ($pattern in $blockedPatterns) {
  try {
    [void][System.Text.RegularExpressions.Regex]::new($pattern)
  }
  catch {
    throw ("POST_APPLY_REGEX_SAFE_COMPILE_FAILED=" + $pattern + "; " + $_.Exception.Message)
  }
  if ($allText -match $pattern) {
    throw ("POST_APPLY_FRONTEND_GUARDRAIL_VIOLATION=" + $pattern)
  }
}

$evidenceRoot = Join-Path $env:TEMP ("local_agents_frontend_v1_post_apply_" + (Get-Date -Format "yyyyMMdd_HHmmssfff"))
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$reportPath = Join-Path $evidenceRoot "post_apply_report.json"
$report = [pscustomobject]@{
  contract = "LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_POST_APPLY"
  generated_at = (Get-Date).ToString("o")
  project_root = $ProjectRoot
  static_asset_contract = "PASS"
  read_only_frontend_guard = "PASS"
  regex_guard_runtime = "PASS"
  token_persistence = "NONE"
  model_execution = "NONE"
  pilot_execution = "NOT_EXECUTED"
  browser_uat = "REQUIRED_NOT_EXECUTED"
  assets = $actualAssets
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
$evidenceArchive = $evidenceRoot + ".zip"
Compress-Archive -Path (Join-Path $evidenceRoot "*") -DestinationPath $evidenceArchive -Force

Write-Output "POST_APPLY_STATIC_ASSET_CONTRACT=PASS"
Write-Output "POST_APPLY_REGEX_SAFE_COMPILE=PASS"
Write-Output "POST_APPLY_READ_ONLY_FRONTEND_GUARD=PASS"
Write-Output "POST_APPLY_NO_TOKEN_PERSISTENCE=PASS"
Write-Output "POST_APPLY_NO_MODEL_OR_PILOT_EXECUTION=PASS"
Write-Output "POST_APPLY_BACKEND_ROUTER_MUTATION=NONE"
Write-Output "POST_APPLY_BACKEND_SCHEMA_MUTATION=NONE"
Write-Output "BROWSER_UAT=REQUIRED_NOT_EXECUTED"
Write-Output ("EVIDENCE_ARCHIVE=" + $evidenceArchive)
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "PROJECT_MUTATION=NONE_DURING_UAT"
Write-Output "SERVICE_START=NONE"
Write-Output "SHELL_EXECUTION=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "EXTERNAL_NETWORK=NONE"
