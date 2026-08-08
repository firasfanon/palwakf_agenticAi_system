param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference='Stop'
$syntax=Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationIdempotentCandidateSyntax.ps1'
$preflight=Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationIdempotentPreflight.ps1'
$whatIf=Join-Path $PackageRoot 'scripts\Install-UnifiedGovernedCapabilityFoundationIdempotentReconciliationV1.ps1'
& $syntax -PackageRoot $PackageRoot
$preflightOutput=@()
$preflightOutput=@(& $preflight -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
$preflightOutput
$line=@($preflightOutput | Where-Object { $_ -is [string] -and $_ -like 'PREFLIGHT_MANIFEST=*' } | Select-Object -Last 1)
if($line.Count -ne 1){throw 'PREFLIGHT_MANIFEST_NOT_EMITTED'}
$preflightManifest=$line.Substring('PREFLIGHT_MANIFEST='.Length)
& $whatIf -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot -PreflightManifest $preflightManifest -WhatIf
