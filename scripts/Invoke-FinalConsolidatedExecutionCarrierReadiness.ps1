param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$syntax = Join-Path $PackageRoot 'scripts\Test-FinalConsolidatedExecutionCarrierCandidateSyntax.ps1'
$preflight = Join-Path $PackageRoot 'scripts\Test-FinalConsolidatedExecutionCarrierPreflight.ps1'
$installer = Join-Path $PackageRoot 'scripts\Install-FinalConsolidatedExecutionCarrier.ps1'
foreach($path in @($syntax,$preflight,$installer)){
  if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ throw ('REQUIRED_SCRIPT_MISSING={0}' -f $path) }
}
& $syntax -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot
$preflightOutput = @()
$preflightOutput = @(& $preflight -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
$preflightOutput
$manifestLines = @($preflightOutput | Where-Object { $_ -is [string] -and $_ -like 'PREFLIGHT_MANIFEST=*' } | Select-Object -Last 1)
if($manifestLines.Count -ne 1){ throw 'PREFLIGHT_MANIFEST_NOT_EMITTED' }
$manifestPath = $manifestLines[0].Substring('PREFLIGHT_MANIFEST='.Length)
& $installer -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot -PreflightManifest $manifestPath -WhatIf
