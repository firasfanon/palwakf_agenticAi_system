[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][string]$PythonExe
)
$ErrorActionPreference='Stop'
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
if(-not(Test-Path $app -PathType Leaf)){throw "APP_PY_NOT_FOUND=$app"}
$appText=Get-Content $app -Raw -Encoding UTF8
$wsImport='from .workspace_core import mount_workspace_core'
$wsMount='mount_workspace_core(app, project_root=PROJECT_ROOT)'
$importCount=([regex]::Matches($appText,[regex]::Escape($wsImport))).Count
$mountCount=([regex]::Matches($appText,[regex]::Escape($wsMount))).Count
"WORKSPACE_CORE_IMPORT_COUNT=$importCount"
"WORKSPACE_CORE_MOUNT_COUNT=$mountCount"
if($importCount -ne 1 -or $mountCount -ne 1){throw 'POST_APPLY_APP_MOUNT_CONTRACT_FAILED'}
& $PythonExe -m py_compile $app
"PY_COMPILE_EXIT_CODE=$LASTEXITCODE"
if($LASTEXITCODE -ne 0){throw 'APP_PY_COMPILE_FAILED'}
"POST_APPLY_APP_MOUNT_CONTRACT=PASS"
"RUNTIME_HTTP_UAT=NOT_EXECUTED"
"LOCAL_SQLITE_RUNTIME_INITIALIZATION=NOT_EXECUTED"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
