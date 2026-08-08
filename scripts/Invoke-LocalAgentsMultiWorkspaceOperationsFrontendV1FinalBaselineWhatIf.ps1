param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$BaselineManifest
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $PackageRoot -PathType Container)) {
  throw ('PACKAGE_ROOT_NOT_FOUND={0}' -f $PackageRoot)
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw ('PROJECT_ROOT_NOT_FOUND={0}' -f $ProjectRoot)
}
if (-not (Test-Path -LiteralPath $BaselineManifest -PathType Leaf)) {
  throw ('BASELINE_MANIFEST_NOT_FOUND={0}' -f $BaselineManifest)
}

$expectedContract = 'LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_FINAL_BASELINE'
$expectedPackageId = 'PALWAKF_LOCAL_AGENTS_FRONTEND_V1_BASELINE_CARRIER_EMPTY_COLLECTION_BINDING_REPAIR_CANDIDATE'
$resolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$appPath = Join-Path $resolvedProjectRoot 'backend/src/palwakf_local_agents/app.py'
if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) {
  throw ('APP_ENTRYPOINT_NOT_FOUND={0}' -f $appPath)
}

$baseline = Get-Content -LiteralPath $BaselineManifest -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
if ($baseline.contract -ne $expectedContract) {
  throw 'BASELINE_CONTRACT_INVALID'
}
if ($baseline.package_id -ne $expectedPackageId) {
  throw 'BASELINE_PACKAGE_BINDING_INVALID'
}
if ($baseline.project_root -ne $resolvedProjectRoot) {
  throw 'BASELINE_PROJECT_ROOT_BINDING_INVALID'
}

$currentAppHash = (Get-FileHash -LiteralPath $appPath -Algorithm SHA256 -ErrorAction Stop).Hash
if ([string]::IsNullOrWhiteSpace([string]$baseline.project_root_hash_anchor)) {
  throw 'BASELINE_APP_ANCHOR_MISSING'
}
if ($baseline.project_root_hash_anchor -ne $currentAppHash) {
  throw 'BASELINE_APP_ANCHOR_DRIFT_DETECTED'
}

'===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 FINAL BASELINE WHATIF ====='
'WHATIF_STATUS=COMPLETE'
'WHATIF_MODE=TRUE'
'BASELINE_BINDING=PASS'
('STATIC_FRONTEND_MODE={0}' -f [string]$baseline.static_frontend_mode)
('KNOWN_WORKSPACE_STATIC_ROOT_STATE={0}' -f [string]$baseline.known_workspace_static_state)
('BASELINE_STATIC_ASSET_COUNT={0}' -f @($baseline.assets).Count)
('BASELINE_ROUTE_INVENTORY_COUNT={0}' -f @($baseline.route_inventory).Count)
('BASELINE_FETCH_INVENTORY_COUNT={0}' -f @($baseline.fetch_inventory).Count)
('BASELINE_FRONTEND_FRAMEWORK_CONFIG_COUNT={0}' -f @($baseline.frontend_framework_inventory).Count)
'FRONTEND_APPLY_CARRIER=NOT_GENERATED_UNTIL_BASELINE_ACCEPTANCE'
'PLANNED_SURFACES=COMMAND_CENTER,WORKSPACE_OVERVIEW,TASKS,PROJECTS,RESEARCH,EVIDENCE,REVIEWS,TOOLS,PILOT_CONTROL,DIAGNOSTICS'
'PLANNED_UI_GUARDS=RTL,DEFAULT_DENY,ACTOR_SCOPE,WORKSPACE_SCOPE,COMMERCIAL_CLIENT_SCOPE,NO_TOKEN_PERSISTENCE,NO_FAKE_DATA'
'PLANNED_PROJECT_MUTATION_SCOPE=STATIC_FRONTEND_ASSETS_AND_UI_TESTS_ONLY_PENDING_EXACT_HASH_BINDING'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SERVICE_START=NONE'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'EXTERNAL_NETWORK=NONE'
'PROJECT_MUTATION=NONE_DURING_WHATIF'
