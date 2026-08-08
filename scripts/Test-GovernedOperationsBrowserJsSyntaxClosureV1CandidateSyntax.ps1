[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot
)
$ErrorActionPreference='Stop'
$package=(Resolve-Path -LiteralPath $PackageRoot).Path
$relative='backend\src\palwakf_local_agents\governed_operations\static\app.js'
$js=Join-Path $package $relative
$required=@(
  $relative,
  'scripts\Install-GovernedOperationsBrowserJsSyntaxClosureV1.ps1',
  'scripts\Test-GovernedOperationsBrowserJsSyntaxClosureV1Preflight.ps1',
  'scripts\Test-GovernedOperationsBrowserJsSyntaxClosureV1Static.ps1',
  'MANIFEST_GOVERNED_OPERATIONS_BROWSER_JS_SYNTAX_CLOSURE_V1.md',
  'APPLY_GUIDE_GOVERNED_OPERATIONS_BROWSER_JS_SYNTAX_CLOSURE_V1_AR.md'
)
$missing=@();foreach($r in $required){if(-not(Test-Path -LiteralPath (Join-Path $package $r) -PathType Leaf)){$missing+=$r}}
$failures=@()
$node=Get-Command node -ErrorAction SilentlyContinue
$nodeCheckExit=-1
if($null -eq $node){$failures+='NODE_NOT_FOUND'}elseif(Test-Path -LiteralPath $js -PathType Leaf){
  & $node.Source --check $js
  $nodeCheckExit=$LASTEXITCODE
  if($nodeCheckExit -ne 0){$failures+="NODE_CHECK_FAILED=$nodeCheckExit"}
}
$jsText=if(Test-Path -LiteralPath $js -PathType Leaf){Get-Content -LiteralPath $js -Raw -Encoding UTF8}else{''}
$malformed=[regex]::Matches($jsText,'\.split\("(\r?\n)"\)').Count
$fixed=[regex]::Matches($jsText,'\.split\("\\n"\)').Count
if($malformed -ne 0){$failures+="MALFORMED_SPLIT_LITERAL_COUNT=$malformed"}
if($fixed -lt 1){$failures+='FIXED_SPLIT_LITERAL_MISSING'}
foreach($needle in @('GOVERNED_OPERATIONS_LOCAL_ONLY','/api/v1/governed-operations','execution_gateway','model_execution','pilot_execution')){if($jsText -notmatch [regex]::Escape($needle)){$failures+="CONTRACT_MARKER_MISSING=$needle"}}
if($jsText -match '(?i)/execute|/dispatch'){$failures+='FORBIDDEN_EXECUTION_ROUTE_REFERENCE'}
Write-Output "REQUIRED_FILE_COUNT=$($required.Count)"
Write-Output "MISSING_FILE_COUNT=$($missing.Count)"
Write-Output "NODE_CHECK_EXIT_CODE=$nodeCheckExit"
Write-Output "MALFORMED_SPLIT_LITERAL_COUNT=$malformed"
Write-Output "FIXED_SPLIT_LITERAL_COUNT=$fixed"
Write-Output 'CANDIDATE_SCOPE=ONE_STATIC_APP_JS_SYNTAX_CLOSURE_ONLY'
Write-Output 'TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY'
Write-Output 'TARGET_MUTATED_FILE=backend/src/palwakf_local_agents/governed_operations/static/app.js'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'PLATFORM_MUTATION=NONE'
Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE'
Write-Output 'LOCAL_PERSISTENT_STATE=UNCHANGED_SQLITE_ONLY'
if($missing.Count -or $failures.Count){Write-Output "VALIDATION_FAILURE_COUNT=$($missing.Count+$failures.Count)";Write-Output "VALIDATION_FAILURES=$(($missing+$failures) -join ';')";Write-Output 'SYNTAX_GATE_RESULT=FAIL';exit 1}
Write-Output 'VALIDATION_FAILURE_COUNT=0';Write-Output 'VALIDATION_FAILURES=';Write-Output 'SYNTAX_GATE_RESULT=PASS'
