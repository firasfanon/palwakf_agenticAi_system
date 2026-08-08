[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$syntax = Join-Path $PackageRoot 'scripts\Test-ReactTypeScriptFrontendFoundationCandidateSyntax.ps1'
$preflight = Join-Path $PackageRoot 'scripts\Test-ReactTypeScriptFrontendFoundationPreflight.ps1'
$whatIf = Join-Path $PackageRoot 'scripts\Invoke-ReactTypeScriptFrontendFoundationWhatIf.ps1'
foreach ($script in @($syntax, $preflight, $whatIf)) { if (-not (Test-Path -LiteralPath $script -PathType Leaf)) { throw "REQUIRED_RUNNER_SCRIPT_NOT_FOUND=$script" } }
& $syntax -PackageRoot $PackageRoot
$preflightOutput = @(& $preflight -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
$preflightOutput
$manifestLine = @($preflightOutput | Where-Object { $_ -is [string] -and $_ -like 'PREFLIGHT_MANIFEST=*' } | Select-Object -Last 1)
if ($manifestLine.Count -ne 1) { throw 'PREFLIGHT_MANIFEST_NOT_EMITTED' }
$preflightManifest = $manifestLine[0].Substring('PREFLIGHT_MANIFEST='.Length)
& $whatIf -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot -PreflightManifest $preflightManifest
Write-Output 'REACT_FRONTEND_FOUNDATION_READINESS_RESULT=PASS'
