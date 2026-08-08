param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

$syntaxScript = Join-Path $PackageRoot 'scripts/Test-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineCarrierSyntax.ps1'
$runtimeScript = Join-Path $PackageRoot 'scripts/Test-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineCarrierRuntime.ps1'
$baselineScript = Join-Path $PackageRoot 'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaseline.ps1'
$whatIfScript = Join-Path $PackageRoot 'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineWhatIf.ps1'

foreach ($requiredPath in @($syntaxScript, $runtimeScript, $baselineScript, $whatIfScript)) {
  if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
    throw ('RUNNER_DEPENDENCY_MISSING={0}' -f $requiredPath)
  }
}

& $syntaxScript -PackageRoot $PackageRoot
& $runtimeScript -PackageRoot $PackageRoot

$baselineOutput = @(& $baselineScript -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
foreach ($line in $baselineOutput) {
  Write-Output $line
}

$baselineManifestLine = $null
foreach ($line in $baselineOutput) {
  if (($line -is [string]) -and $line.StartsWith('BASELINE_MANIFEST=')) {
    $baselineManifestLine = $line
  }
}

if ([string]::IsNullOrWhiteSpace($baselineManifestLine)) {
  throw 'BASELINE_MANIFEST_NOT_EMITTED'
}

$baselineManifest = $baselineManifestLine.Substring('BASELINE_MANIFEST='.Length)
if (-not (Test-Path -LiteralPath $baselineManifest -PathType Leaf)) {
  throw ('BASELINE_MANIFEST_NOT_CREATED={0}' -f $baselineManifest)
}

& $whatIfScript -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot -BaselineManifest $baselineManifest

'===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 FINAL BASELINE CARRIER RUNNER ====='
'FINAL_BASELINE_RUNNER_RESULT=PASS'
'PROJECT_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SERVICE_START=NONE'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'EXTERNAL_NETWORK=NONE'
