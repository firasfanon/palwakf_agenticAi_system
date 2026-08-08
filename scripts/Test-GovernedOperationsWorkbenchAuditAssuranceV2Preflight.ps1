[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$expected=@{
  'backend/src/palwakf_local_agents/governed_operations/__init__.py' = '7552AFBAB693E7E7A13D11EE81146027059175F1BFA66DBDEA9F448DBABD95F3'
  'backend/src/palwakf_local_agents/governed_operations/contracts.py' = 'BC5E26AA7233A047867A78B2C87179A168C047315ADBE495D53C5530479FEDC8'
  'backend/src/palwakf_local_agents/governed_operations/store.py' = '47078813C1CDCDFD2B09971458E03F3D60F73E37DFCB62FB2796289FB90B7207'
  'backend/src/palwakf_local_agents/governed_operations/router.py' = '5E192F04EE75B603193D734324D6D24BA5B443917F4FDC6F86FE8B015B656810'
  'backend/src/palwakf_local_agents/governed_operations/static/index.html' = '57B681746E299739675D8028301945A968A92D5757F154129CF058AC6799BA45'
  'backend/src/palwakf_local_agents/governed_operations/static/styles.css' = 'E110BF2A9CB6CD6ECF658C62D5754FA174CEF52EA2570CE745B9ECAA81D1C52B'
  'backend/src/palwakf_local_agents/governed_operations/static/app.js' = '9379BD8826DF41AF456B601A578EDF294E9DDD029B2F4EED242DFD9B102FF041'
  'backend/tests/test_governed_operations.py' = 'B1051D5952AC6460E1B322DE938DB443A36B7E98D34A79AC2E7FACFEA7C499E6'
}
foreach($relative in $expected.Keys){
  $path=Join-Path $ProjectRoot $relative.Replace('/','\')
  if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "BASELINE_FILE_MISSING=$relative"}
  $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  "TARGET_PREIMAGE_SHA256[$relative]=$actual"
  if($actual -ne $expected[$relative]){throw "UNEXPECTED_PREIMAGE_SHA256[$relative]=$actual"}
}
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$appText=Get-Content -LiteralPath $app -Raw -Encoding UTF8
if($appText -notmatch [regex]::Escape('from .governed_operations import mount_governed_operations')){throw 'GOVERNED_OPERATIONS_MOUNT_IMPORT_NOT_FOUND'}
if($appText -notmatch [regex]::Escape('mount_governed_operations(app, project_root=PROJECT_ROOT)')){throw 'GOVERNED_OPERATIONS_MOUNT_CALL_NOT_FOUND'}
$cc=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\command_center\static\app.js'
$ccHash=(Get-FileHash -LiteralPath $cc -Algorithm SHA256).Hash
"COMMAND_CENTER_CURRENT_SHA256=$ccHash"
if($ccHash -ne 'D83F8709428C047D9229ACD9C232BF1F552A078BBBA42B141D7FF7566006CD1E'){throw "COMMAND_CENTER_EVENT_LISTENER_POSTIMAGE_NOT_PRESENT=$ccHash"}
$docsExist=Test-Path -LiteralPath (Join-Path $ProjectRoot 'docs\governed_operations')
"GOVERNED_OPERATIONS_DOCS_DIRECTORY_EXISTS=$docsExist"
"PREFLIGHT_RESULT=PASS"
"TARGET_MUTATION_SCOPE=GOVERNED_OPERATIONS_MODULE_TESTS_AND_DOCS_ONLY"
"COMMAND_CENTER_MUTATION=NONE"
"APP_ENTRYPOINT_MUTATION=NONE"
"LOCAL_SQLITE_SCHEMA_MIGRATION=ON_FIRST_GOVERNED_OPERATIONS_RUNTIME_ACCESS_ONLY"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
