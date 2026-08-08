[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$expected=@{
  'backend/src/palwakf_local_agents/workspace_core/static/index.html' = '9A08B87F1855C9CB9B4899924A3B1B390C8FB76D967A9B4C67DE753576F9D1E9'
  'backend/src/palwakf_local_agents/workspace_core/static/styles.css' = '645C7FFA5B65CA57E7B9CC894D21479EF9530A39B9C9146590C9DBAD2C83F9E0'
  'backend/src/palwakf_local_agents/workspace_core/static/app.js' = '5A64C5BDF78C8E25AF83EF457153EB612B2CD2C1B9C4B4BDE5E20EB1B40A11CE'
  'backend/tests/test_workspace_core.py' = '3FF26C41DF99547581BC2059DA709272CA1227D17A4A813B9728F064984ECA29'
}
$fail=@()
foreach($relative in $expected.Keys){
  $target=Join-Path $ProjectRoot $relative
  $candidate=Join-Path $PackageRoot $relative
  if(-not(Test-Path $target -PathType Leaf)){$fail+="TARGET_FILE_MISSING=$relative";continue}
  if(-not(Test-Path $candidate -PathType Leaf)){$fail+="CANDIDATE_FILE_MISSING=$relative";continue}
  $actual=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  "TARGET_PREIMAGE_SHA256[$relative]=$actual"
  if($actual -ne $expected[$relative]){$fail+="UNEXPECTED_PREIMAGE_SHA256[$relative]=$actual"}
}
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
if(-not(Test-Path $app -PathType Leaf)){$fail+='APP_PY_MISSING'}else{
  $appText=Get-Content -LiteralPath $app -Raw -Encoding UTF8
  $importCount=([regex]::Matches($appText,'(?m)^\s*from \.workspace_core import mount_workspace_core\s*$')).Count
  $mountCount=([regex]::Matches($appText,'(?m)^\s*mount_workspace_core\(app,\s*project_root=PROJECT_ROOT\)\s*$')).Count
  "WORKSPACE_CORE_IMPORT_COUNT=$importCount";"WORKSPACE_CORE_MOUNT_COUNT=$mountCount"
  if($importCount -ne 1){$fail+="WORKSPACE_CORE_IMPORT_COUNT_INVALID=$importCount"}
  if($mountCount -ne 1){$fail+="WORKSPACE_CORE_MOUNT_COUNT_INVALID=$mountCount"}
}
$core=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\workspace_core'
$protected=@('store.py','router.py','contracts.py','policy.py','__init__.py')
foreach($f in $protected){if(-not(Test-Path (Join-Path $core $f) -PathType Leaf)){$fail+="PROTECTED_CORE_FILE_MISSING=$f"}}
"PREFLIGHT_FAILURE_COUNT=$($fail.Count)";"PREFLIGHT_FAILURES=$($fail -join ';')"
"TARGET_MUTATION_SCOPE=WORKSPACE_CORE_UI_ASSETS_TESTS_AND_DOCS_ONLY"
"APP_ENTRYPOINT_MUTATION=NONE";"CORE_API_MUTATION=NONE";"POLICY_PACK_MUTATION=NONE";"COMMAND_CENTER_MUTATION=NONE";"GOVERNED_OPERATIONS_MUTATION=NONE";"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED"
if($fail.Count){throw 'PREFLIGHT_FAILED'}
"PREFLIGHT_RESULT=PASS"
