[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@('backend/src/palwakf_local_agents/command_center/static/index.html','backend/src/palwakf_local_agents/command_center/static/styles.css','backend/src/palwakf_local_agents/command_center/static/app.js','scripts/Test-CommandCenterNarrowViewportResponsiveClosureV1Preflight.ps1','scripts/Test-CommandCenterNarrowViewportResponsiveClosureV1StaticEval.ps1','scripts/Install-CommandCenterNarrowViewportResponsiveClosureV1.ps1','docs/README_COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1_AR.md','docs/SECURITY_CONTRACT_COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1.md','docs/UAT_COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1_AR.md','docs/CHANGELOG_COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1.md')
$missing=@($required|Where-Object{-not(Test-Path -LiteralPath (Join-Path $PackageRoot $_) -PathType Leaf)})
"REQUIRED_FILE_COUNT=$($required.Count)";"MISSING_FILE_COUNT=$($missing.Count)";"MISSING_FILES=$($missing -join ';')"
if($missing.Count){throw 'CANDIDATE_REQUIRED_FILE_MISSING'}
$app=Join-Path $PackageRoot 'backend/src/palwakf_local_agents/command_center/static/app.js'
$css=Join-Path $PackageRoot 'backend/src/palwakf_local_agents/command_center/static/styles.css'
$index=Join-Path $PackageRoot 'backend/src/palwakf_local_agents/command_center/static/index.html'
$node=Get-Command node -ErrorAction SilentlyContinue
if($node){& $node.Source --check $app;if($LASTEXITCODE -ne 0){throw 'NODE_APP_JS_CHECK_FAILED'}; 'NODE_APP_JS_CHECK=PASS'}else{'NODE_APP_JS_CHECK=NOT_AVAILABLE'}
$checks=@(
 @{n='NARROW_VIEWPORT_CONTRACT';v=(Get-Content $app -Raw -Encoding UTF8).Contains('COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1')},
 @{n='EVENT_DELEGATION_RETAINED';v=(Get-Content $app -Raw -Encoding UTF8).Contains('window.__PWF_COMMAND_CENTER_UI_BOUND__')},
 @{n='NO_TIMER_LOOP';v=(-not ((Get-Content $app -Raw -Encoding UTF8) -match 'setInterval\s*\(|setTimeout\s*\(|requestAnimationFrame\s*\('))},
 @{n='SIDEBAR_SCRIM_MARKUP';v=(Get-Content $index -Raw -Encoding UTF8).Contains('sidebar-scrim')},
 @{n='MOBILE_OVERFLOW_GUARDS';v=((Get-Content $css -Raw -Encoding UTF8).Contains('overflow-x:hidden') -and (Get-Content $css -Raw -Encoding UTF8).Contains('COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1')}
)
$fail=@($checks|Where-Object{-not $_.v});"CONTRACT_MARKER_FAILURE_COUNT=$($fail.Count)";"CONTRACT_MARKER_FAILURES=$(($fail.n) -join ';')"; 'CANDIDATE_SCOPE=COMMAND_CENTER_STATIC_UI_ONLY';'APP_ENTRYPOINT_MUTATION=NONE';'API_MUTATION=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';if($fail.Count){throw 'CANDIDATE_CONTRACT_MARKER_FAILURE'};'SYNTAX_GATE_RESULT=PASS'
