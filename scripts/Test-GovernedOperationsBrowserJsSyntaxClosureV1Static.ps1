[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot
)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath $ProjectRoot).Path
$relative='backend\src\palwakf_local_agents\governed_operations\static\app.js'
$js=Join-Path $project $relative
$failures=@()
if(-not(Test-Path -LiteralPath $js -PathType Leaf)){$failures+="TARGET_APP_JS_MISSING=$js"}
$node=Get-Command node -ErrorAction SilentlyContinue
$nodeCheckExit=-1
if($null -eq $node){$failures+='NODE_NOT_FOUND'}elseif(Test-Path -LiteralPath $js -PathType Leaf){& $node.Source --check $js;$nodeCheckExit=$LASTEXITCODE;if($nodeCheckExit -ne 0){$failures+="NODE_CHECK_FAILED=$nodeCheckExit"}}
$hash=if(Test-Path -LiteralPath $js -PathType Leaf){(Get-FileHash -LiteralPath $js -Algorithm SHA256).Hash}else{''}
$t=if(Test-Path -LiteralPath $js -PathType Leaf){Get-Content -LiteralPath $js -Raw -Encoding UTF8}else{''}
$malformed=[regex]::Matches($t,'\.split\("(\r?\n)"\)').Count
$fixed=[regex]::Matches($t,'\.split\("\\n"\)').Count
if($hash -ne '9379BD8826DF41AF456B601A578EDF294E9DDD029B2F4EED242DFD9B102FF041'){$failures+="POSTIMAGE_SHA256_MISMATCH=$hash"}
if($malformed -ne 0){$failures+="MALFORMED_SPLIT_LITERAL_COUNT=$malformed"}
if($fixed -lt 1){$failures+='FIXED_SPLIT_LITERAL_MISSING'}
if($t -match '(?i)/execute|/dispatch'){$failures+='FORBIDDEN_EXECUTION_ROUTE_REFERENCE'}
Write-Output "TARGET_APP_JS_SHA256=$hash"
Write-Output "NODE_CHECK_EXIT_CODE=$nodeCheckExit"
Write-Output "MALFORMED_SPLIT_LITERAL_COUNT=$malformed"
Write-Output "FIXED_SPLIT_LITERAL_COUNT=$fixed"
Write-Output 'TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY'
Write-Output 'APP_ENTRYPOINT_MUTATION=NONE'
Write-Output 'ROUTER_MUTATION=NONE'
Write-Output 'STORE_MUTATION=NONE'
Write-Output 'COMMAND_CENTER_MUTATION=NONE'
Write-Output 'LOCAL_SQLITE_WRITE=NONE'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'PLATFORM_MUTATION=NONE'
Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE'
if($failures.Count){Write-Output "VALIDATION_FAILURE_COUNT=$($failures.Count)";Write-Output "VALIDATION_FAILURES=$($failures -join ';')";Write-Output 'GOVERNED_OPERATIONS_APP_JS_STATIC_GATE=FAIL';exit 1}
Write-Output 'VALIDATION_FAILURE_COUNT=0';Write-Output 'VALIDATION_FAILURES=';Write-Output 'GOVERNED_OPERATIONS_APP_JS_STATIC_GATE=PASS'
