[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$syntaxScript = Join-Path $PackageRoot "scripts\Test-MegaBatch01To06UnifiedCandidateSyntax.ps1"
$preflightScript = Join-Path $PackageRoot "scripts\Invoke-MegaBatch01To06UnifiedBaselinePreflight.ps1"
$whatIfScript = Join-Path $PackageRoot "scripts\Invoke-MegaBatch01To06UnifiedPlanningWhatIf.ps1"

foreach ($requiredPath in @($PackageRoot, $ProjectRoot, $syntaxScript, $preflightScript, $whatIfScript)) {
  if (-not (Test-Path -LiteralPath $requiredPath)) {
    throw ("REQUIRED_PATH_NOT_FOUND={0}" -f $requiredPath)
  }
}

& $syntaxScript -PackageRoot $PackageRoot

$preflightOutput = @()
try {
  $preflightOutput = @(& $preflightScript -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
}
catch {
  throw ("UNIFIED_PREFLIGHT_EXECUTION_FAILED={0}" -f $_.Exception.Message)
}

$manifestLine = @(
  $preflightOutput |
  Where-Object { $_ -is [string] -and $_ -like "PREFLIGHT_MANIFEST=*" } |
  Select-Object -Last 1
)
if ($manifestLine.Count -ne 1) {
  throw "PREFLIGHT_MANIFEST_NOT_EMITTED"
}

$preflightManifest = $manifestLine.Substring("PREFLIGHT_MANIFEST=".Length)
if (-not (Test-Path -LiteralPath $preflightManifest -PathType Leaf)) {
  throw "PREFLIGHT_MANIFEST_PATH_INVALID"
}

& $whatIfScript -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot -PreflightManifest $preflightManifest
