[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$expected=@{
 'backend/src/palwakf_local_agents/command_center/static/index.html'='5BD79046631508DED2019714892DA4295CB093C4D04518D10B72D66DBCC98D99'
 'backend/src/palwakf_local_agents/command_center/static/styles.css'='709142B65FD47748F928118696DD3F45D363DB6A80E5636DB4D19811B22E8144'
 'backend/src/palwakf_local_agents/command_center/static/app.js'='D83F8709428C047D9229ACD9C232BF1F552A078BBBA42B141D7FF7566006CD1E'
}
$fail=@();foreach($relative in $expected.Keys){$target=Join-Path $ProjectRoot $relative;if(-not(Test-Path -LiteralPath $target -PathType Leaf)){$fail+="MISSING_TARGET_FILE[$relative]";continue};$actual=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash;"TARGET_PREIMAGE_SHA256[$relative]=$actual";if($actual -ne $expected[$relative]){$fail+="UNEXPECTED_PREIMAGE_SHA256[$relative]=$actual"}}
$app=Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/app.py';$appText=Get-Content -LiteralPath $app -Raw -Encoding UTF8;$mountCount=([regex]::Matches($appText,'(?m)^\s*mount_command_center\(app,\s*project_root=PROJECT_ROOT\)\s*$')).Count;"COMMAND_CENTER_MOUNT_COUNT=$mountCount";if($mountCount -ne 1){$fail+="COMMAND_CENTER_MOUNT_COUNT_INVALID=$mountCount"}
"PREFLIGHT_FAILURE_COUNT=$($fail.Count)";"PREFLIGHT_FAILURES=$($fail -join ';')";'TARGET_MUTATION_SCOPE=COMMAND_CENTER_STATIC_ASSETS_ONLY';'APP_ENTRYPOINT_MUTATION=NONE';'API_MUTATION=NONE';'GOVERNED_OPERATIONS_MUTATION=NONE';'WORKSPACE_CORE_MUTATION=NONE';'LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';if($fail.Count){throw 'PREFLIGHT_FAILED'};'PREFLIGHT_RESULT=PASS'
