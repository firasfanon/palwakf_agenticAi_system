[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$cc=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\command_center\static\app.js'
$go=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\governed_operations\store.py'
$fail=@()
foreach($p in @($app,$cc,$go)){if(-not(Test-Path $p -PathType Leaf)){$fail+="MISSING=$p"}}
if($fail.Count){"PREFLIGHT_FAILURE_COUNT=$($fail.Count)";"PREFLIGHT_FAILURES=$($fail -join ';')";throw 'PREFLIGHT_REQUIRED_BASELINE_MISSING'}
$appText=Get-Content $app -Raw -Encoding UTF8
if($appText -notmatch [regex]::Escape('from .governed_operations import mount_governed_operations')){$fail+='GOVERNED_OPERATIONS_IMPORT_BASELINE_MISSING'}
if($appText -notmatch [regex]::Escape('mount_governed_operations(app, project_root=PROJECT_ROOT)')){$fail+='GOVERNED_OPERATIONS_MOUNT_BASELINE_MISSING'}
if($appText -match [regex]::Escape('mount_workspace_core(app, project_root=PROJECT_ROOT)')){$fail+='WORKSPACE_CORE_ALREADY_MOUNTED'}
if(Test-Path (Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\workspace_core')){$fail+='WORKSPACE_CORE_DIRECTORY_ALREADY_EXISTS'}
"PREFLIGHT_FAILURE_COUNT=$($fail.Count)";"PREFLIGHT_FAILURES=$($fail -join ';')"
"PATCH_SCOPE=NEW_WORKSPACE_CORE_POLICY_PACKS_TESTS_DOCS_PLUS_EXPLICIT_APP_MOUNT"
"COMMAND_CENTER_MUTATION=NONE";"GOVERNED_OPERATIONS_MUTATION=NONE";"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL";"LEGACY_MIGRATION=NONE";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED"
if($fail.Count){throw 'PREFLIGHT_FAILED'}
"PREFLIGHT_RESULT=PASS"
