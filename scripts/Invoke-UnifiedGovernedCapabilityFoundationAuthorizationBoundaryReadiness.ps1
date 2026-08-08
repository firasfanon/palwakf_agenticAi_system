param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$syntax=Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryCandidateSyntax.ps1'
$preflight=Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryPreflight.ps1'
$installer=Join-Path $PackageRoot 'scripts\Install-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryV1.ps1'
& $syntax -PackageRoot $PackageRoot
$preflightOutput=@(& $preflight -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
$preflightOutput
$line=@($preflightOutput|Where-Object {$_ -is [string] -and $_ -like 'PREFLIGHT_MANIFEST=*'}|Select-Object -Last 1)
if($line.Count -ne 1){throw 'PREFLIGHT_MANIFEST_NOT_EMITTED'}
$manifest=$line.Substring('PREFLIGHT_MANIFEST='.Length)
& $installer -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot -PreflightManifest $manifest -WhatIf
