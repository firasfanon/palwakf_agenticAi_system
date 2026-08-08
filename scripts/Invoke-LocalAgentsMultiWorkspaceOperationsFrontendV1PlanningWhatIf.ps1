param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][string]$BaselineManifest
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $BaselineManifest -PathType Leaf)) {
  throw ('BASELINE_MANIFEST_NOT_FOUND={0}' -f $BaselineManifest)
}

$baseline = Get-Content -LiteralPath $BaselineManifest -Raw -Encoding UTF8 | ConvertFrom-Json
$expectedPackageId = 'PALWAKF_LOCAL_AGENTS_MEGA_BATCH_LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_DESIGN_BASELINE_CANDIDATE'
if ($baseline.contract -ne 'LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_BASELINE') {
  throw 'BASELINE_CONTRACT_INVALID'
}
if ($baseline.package_id -ne $expectedPackageId) {
  throw 'BASELINE_PACKAGE_BINDING_INVALID'
}
if ($baseline.project_root -ne $ProjectRoot) {
  throw 'BASELINE_PROJECT_ROOT_BINDING_INVALID'
}

$currentApp = Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/app.py'
$currentAppHash = (Get-FileHash -LiteralPath $currentApp -Algorithm SHA256).Hash
if ($baseline.project_root_hash_anchor -and ($baseline.project_root_hash_anchor -ne $currentAppHash)) {
  throw 'BASELINE_APP_ANCHOR_DRIFT_DETECTED'
}

$staticRootState = [string]$baseline.known_workspace_static_state
$mode = [string]$baseline.static_frontend_mode

'===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 PLANNING WHATIF ====='
'WHATIF_STATUS=COMPLETE'
'WHATIF_MODE=TRUE'
('BASELINE_BINDING=PASS')
('STATIC_FRONTEND_MODE={0}' -f $mode)
('KNOWN_WORKSPACE_STATIC_ROOT_STATE={0}' -f $staticRootState)
'FRONTEND_APPLY_CARRIER=NOT_GENERATED_UNTIL_BASELINE_ACCEPTANCE'
'PLANNED_SURFACES=COMMAND_CENTER,WORKSPACE_OVERVIEW,TASKS,PROJECTS,RESEARCH,EVIDENCE,REVIEWS,TOOLS,PILOT_CONTROL,DIAGNOSTICS'
'PLANNED_UI_GUARDS=RTL,DEFAULT_DENY,ACTOR_SCOPE,WORKSPACE_SCOPE,COMMERCIAL_CLIENT_SCOPE,NO_TOKEN_PERSISTENCE,NO_FAKE_DATA'
'PLANNED_PROJECT_MUTATION_SCOPE=STATIC_FRONTEND_ASSETS_AND_UI_TESTS_ONLY_PENDING_EXACT_HASH_BINDING'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'EXTERNAL_NETWORK=NONE'
'PROJECT_MUTATION=NONE_DURING_WHATIF'
