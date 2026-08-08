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

$syntax = Join-Path $PackageRoot "scripts\Test-LocalAgentsMultiWorkspaceOperationsFrontendV1CandidateSyntax.ps1"
$preflight = Join-Path $PackageRoot "scripts\Test-LocalAgentsMultiWorkspaceOperationsFrontendV1Preflight.ps1"

& $syntax -PackageRoot $PackageRoot

$preflightOutput = @(& $preflight -PackageRoot $PackageRoot -ProjectRoot $ProjectRoot)
$preflightOutput

$manifestLine = @($preflightOutput | Where-Object { $_ -is [string] -and $_ -like "PREFLIGHT_MANIFEST=*" } | Select-Object -Last 1)
if ($manifestLine.Count -ne 1) {
  throw "PREFLIGHT_MANIFEST_NOT_EMITTED"
}
$manifestPath = $manifestLine[0].Substring("PREFLIGHT_MANIFEST=".Length)
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json

Write-Output "===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 WHATIF ====="
Write-Output "WHATIF_STATUS=COMPLETE"
Write-Output "WHATIF_MODE=TRUE"
Write-Output "BASELINE_BINDING=PASS"
Write-Output ("PREDICTED_STATIC_ASSET_REPLACEMENT_COUNT=" + [string]$manifest.preimage_asset_count)
Write-Output ("PREDICTED_STATIC_ASSET_NOOP_COUNT=" + [string]$manifest.exact_postimage_asset_count)
Write-Output "PREDICTED_BACKEND_ROUTER_MUTATION_COUNT=0"
Write-Output "PREDICTED_BACKEND_SCHEMA_MUTATION_COUNT=0"
Write-Output "PREDICTED_MODEL_EXECUTION_COUNT=0"
Write-Output "PREDICTED_PILOT_EXECUTION_COUNT=0"
Write-Output "PREDICTED_FRONTEND_WRITE_REQUEST_COUNT=0"
Write-Output "PREDICTED_TOKEN_PERSISTENCE_COUNT=0"
Write-Output "BROWSER_UAT=NOT_EXECUTED"
Write-Output "PROJECT_MUTATION=NONE_DURING_WHATIF"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "SERVICE_START=NONE"
Write-Output "SHELL_EXECUTION=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "EXTERNAL_NETWORK=NONE"
Write-Output "FRONTEND_READINESS_RESULT=PASS"
