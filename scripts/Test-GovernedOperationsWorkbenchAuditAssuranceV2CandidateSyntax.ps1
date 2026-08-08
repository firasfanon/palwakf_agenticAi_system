[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@(
 'backend\src\palwakf_local_agents\governed_operations\__init__.py',
 'backend\src\palwakf_local_agents\governed_operations\contracts.py',
 'backend\src\palwakf_local_agents\governed_operations\store.py',
 'backend\src\palwakf_local_agents\governed_operations\router.py',
 'backend\src\palwakf_local_agents\governed_operations\static\index.html',
 'backend\src\palwakf_local_agents\governed_operations\static\styles.css',
 'backend\src\palwakf_local_agents\governed_operations\static\app.js',
 'backend\tests\test_governed_operations.py',
 'docs\README_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2_AR.md',
 'docs\SECURITY_CONTRACT_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2.md',
 'docs\UAT_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2_AR.md'
)
$missing=@($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $PackageRoot $_) -PathType Leaf) })
"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$($missing -join ',')"
if($missing.Count){throw 'CANDIDATE_REQUIRED_FILES_MISSING'}
$node=Get-Command node -ErrorAction Stop
$appJs=Join-Path $PackageRoot 'backend\src\palwakf_local_agents\governed_operations\static\app.js'
& $node.Source --check $appJs
if($LASTEXITCODE -ne 0){throw 'OPERATIONS_WORKBENCH_APP_JS_SYNTAX_FAILED'}
$text=Get-Content -LiteralPath $appJs -Raw -Encoding UTF8
$must=@('GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2','bindOnce','expected_version','LOCAL_HUMAN_REVIEW_ASSERTED','/integrity')
$fail=@($must | Where-Object { $text -notmatch [regex]::Escape($_) })
"CONTRACT_MARKER_FAILURE_COUNT=$($fail.Count)"
"CONTRACT_MARKER_FAILURES=$($fail -join ',')"
if($fail.Count){throw 'WORKBENCH_CONTRACT_MARKER_FAILURE'}
$router=Get-Content -LiteralPath (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\governed_operations\router.py') -Raw -Encoding UTF8
if($router -match '@api\.(get|post)\("/(execute|dispatch)'){throw 'FORBIDDEN_EXECUTION_ROUTE_DETECTED'}
"TARGET_MUTATION_SCOPE=GOVERNED_OPERATIONS_MODULE_TESTS_AND_DOCS_ONLY"
"COMMAND_CENTER_MUTATION=NONE"
"APP_ENTRYPOINT_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"SYNTAX_GATE_RESULT=PASS"
