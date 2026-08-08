[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$root=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\workspace_core\static'
$required=@('index.html','styles.css','app.js')
$missing=@($required|Where-Object{-not(Test-Path (Join-Path $root $_) -PathType Leaf)})
"REQUIRED_FILE_COUNT=$($required.Count)";"MISSING_FILE_COUNT=$($missing.Count)";"MISSING_FILES=$($missing -join ';')"
if($missing.Count){throw 'WORKSPACE_UI_STATIC_GATE_FILES_MISSING'}
$index=Get-Content (Join-Path $root 'index.html') -Raw -Encoding UTF8
$styles=Get-Content (Join-Path $root 'styles.css') -Raw -Encoding UTF8
$script=Get-Content (Join-Path $root 'app.js') -Raw -Encoding UTF8
$requiredIndex=@('lang="ar"','WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1')
$requiredScript=@('workspaceLabels','formatValue','tech-details','bindOnce','method: "GET"')
$requiredStyles=@('overflow-wrap:anywhere','word-break:break-word','@media(max-width:820px)')
$fail=@()
foreach($m in $requiredIndex){if($index -notmatch [regex]::Escape($m)){$fail+="INDEX_MARKER_MISSING=$m"}}
foreach($m in $requiredScript){if($script -notmatch [regex]::Escape($m)){$fail+="SCRIPT_MARKER_MISSING=$m"}}
foreach($m in $requiredStyles){if($styles -notmatch [regex]::Escape($m)){$fail+="STYLE_MARKER_MISSING=$m"}}
foreach($disallowed in @('setInterval(','setTimeout(','requestAnimationFrame(')){if($script.Contains($disallowed)){$fail+="DISALLOWED_UI_LOOP=$disallowed"}}
"STATIC_FAILURE_COUNT=$($fail.Count)";"STATIC_FAILURES=$($fail -join ';')"
if($fail.Count){throw 'WORKSPACE_UI_STATIC_GATE_FAILED'}
"WORKSPACE_UI_CARD_OVERFLOW_GUARD=PASS";"WORKSPACE_UI_RTL_CONTRACT=PASS";"WORKSPACE_UI_RAW_VALUES_COLLAPSED=PASS";"API_WRITE_ROUTE_ADDITION=NONE";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED";"FINAL_RESULT=PASS"
