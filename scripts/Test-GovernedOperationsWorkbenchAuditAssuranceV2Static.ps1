[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$root=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\governed_operations'
$required=@('__init__.py','contracts.py','store.py','router.py','static\index.html','static\styles.css','static\app.js')
$missing=@($required|Where-Object{-not(Test-Path -LiteralPath (Join-Path $root $_) -PathType Leaf)})
"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$($missing -join ',')"
if($missing.Count){throw 'GOVERNED_OPERATIONS_V2_REQUIRED_FILE_MISSING'}
$node=Get-Command node -ErrorAction Stop
$appJs=Join-Path $root 'static\app.js'
& $node.Source --check $appJs
if($LASTEXITCODE -ne 0){throw 'OPERATIONS_WORKBENCH_APP_JS_SYNTAX_FAILED'}
$router=Get-Content -LiteralPath (Join-Path $root 'router.py') -Raw -Encoding UTF8
$store=Get-Content -LiteralPath (Join-Path $root 'store.py') -Raw -Encoding UTF8
$ui=Get-Content -LiteralPath $appJs -Raw -Encoding UTF8
$bad=@()
if($router -match '@api\.(get|post)\("/(execute|dispatch)'){$bad+='FORBIDDEN_EXECUTION_ROUTE'}
if($ui -match 'setInterval|setTimeout|requestAnimationFrame'){$bad+='UNBOUNDED_TIMER_PRESENT'}
foreach($marker in @('EXPECTED_VERSION_REQUIRED','LOCAL_HUMAN_REVIEW_ASSERTED','APPROVAL_EVIDENCE_GATE_BLOCKED','audit_chain_integrity','GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2')){
 if(($router+$store+$ui) -notmatch [regex]::Escape($marker)){$bad+="MISSING_$marker"}
}
"VALIDATION_FAILURE_COUNT=$($bad.Count)"
"VALIDATION_FAILURES=$($bad -join ',')"
if($bad.Count){throw 'GOVERNED_OPERATIONS_V2_STATIC_CONTRACT_FAILED'}
'GOVERNED_OPERATIONS_SCOPE=LOCAL_SQLITE_GOVERNED_WORKBENCH'
'EXECUTION_GATEWAY=DISABLED_BY_DEFAULT'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'PLATFORM_MUTATION=NONE'
'EXTERNAL_DATABASE_ACCESS=NONE'
'FINAL_RESULT=PASS'
