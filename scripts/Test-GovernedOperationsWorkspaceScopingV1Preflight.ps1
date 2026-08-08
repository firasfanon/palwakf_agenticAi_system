[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PackageRoot,[string]$EvidenceRoot="$env:TEMP")
$ErrorActionPreference='Stop'
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
$required=@(
 'backend/src/palwakf_local_agents/app.py',
 'backend/src/palwakf_local_agents/governed_operations/__init__.py',
 'backend/src/palwakf_local_agents/governed_operations/contracts.py',
 'backend/src/palwakf_local_agents/governed_operations/store.py',
 'backend/src/palwakf_local_agents/governed_operations/router.py',
 'backend/src/palwakf_local_agents/governed_operations/static/index.html',
 'backend/src/palwakf_local_agents/governed_operations/static/styles.css',
 'backend/src/palwakf_local_agents/governed_operations/static/app.js',
 'backend/src/palwakf_local_agents/workspace_core/store.py',
 'backend/src/palwakf_local_agents/workspace_core/router.py',
 'policy_packs/government_strict_v1/policy.json',
 'policy_packs/developer_controlled_v1/policy.json',
 'policy_packs/client_isolated_v1/policy.json',
 'policy_packs/research_read_prepare_v1/policy.json'
)
$fail=@();$manifest=@{}
foreach($relative in $required){$path=Join-Path $ProjectRoot $relative;if(-not(Test-Path -LiteralPath $path -PathType Leaf)){$fail+="MISSING_REQUIRED=$relative"}else{$manifest[$relative]=Hash $path}}
$app=Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/app.py') -Raw -Encoding UTF8
if(([regex]::Matches($app,'mount_workspace_core\(app, project_root=PROJECT_ROOT\)').Count)-ne 1){$fail+='WORKSPACE_CORE_MOUNT_COUNT_NOT_ONE'}
if(([regex]::Matches($app,'mount_governed_operations\(app, project_root=PROJECT_ROOT\)').Count)-ne 1){$fail+='GOVERNED_OPERATIONS_MOUNT_COUNT_NOT_ONE'}
$router=Get-Content -LiteralPath (Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/governed_operations/router.py') -Raw -Encoding UTF8
if($router.Contains('GOVERNED_OPERATIONS_WORKSPACE_SCOPING_V1')){$fail+='WORKSPACE_SCOPING_ALREADY_PRESENT_RECONCILIATION_REQUIRED'}
$timestamp=Get-Date -Format 'yyyyMMdd_HHmmss';$dir=Join-Path $EvidenceRoot "governed_operations_workspace_scoping_v1_preflight_$timestamp";New-Item -ItemType Directory -Path $dir -Force|Out-Null
$manifestPath=Join-Path $dir 'preflight_preimage_manifest.json'
[ordered]@{contract='GOVERNED_OPERATIONS_WORKSPACE_SCOPING_V1';project_root=$ProjectRoot;created_at=(Get-Date).ToUniversalTime().ToString('o');files=$manifest}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $manifestPath -Encoding UTF8
$manifest.GetEnumerator()|Sort-Object Name|ForEach-Object{"TARGET_PREIMAGE_SHA256[$($_.Name)]=$($_.Value)"}
"PREFLIGHT_MANIFEST=$manifestPath"
'APP_ENTRYPOINT_MUTATION=NONE'
'WORKSPACE_CORE_SOURCE_MUTATION=NONE'
'POLICY_PACK_MUTATION=NONE'
'COMMAND_CENTER_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
if($fail.Count){"PREFLIGHT_FAILURE_COUNT=$($fail.Count)";$fail;throw 'PREFLIGHT_FAILED'}
'PREFLIGHT_FAILURE_COUNT=0'
'PREFLIGHT_RESULT=PASS'
