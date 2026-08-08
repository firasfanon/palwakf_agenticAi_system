[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$app=Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/command_center/static/app.js';$css=Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/command_center/static/styles.css';$index=Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/command_center/static/index.html'
$js=Get-Content $app -Raw -Encoding UTF8;$styles=Get-Content $css -Raw -Encoding UTF8;$html=Get-Content $index -Raw -Encoding UTF8
$checks=@(
 @{n='NARROW_VIEWPORT_CONTRACT_PRESENT';v=$js.Contains('COMMAND_CENTER_NARROW_VIEWPORT_RESPONSIVE_CLOSURE_V1')},
 @{n='DRAWER_SCRIM_PRESENT';v=($html.Contains('sidebar-scrim') -and $js.Contains('setSidebar'))},
 @{n='ESCAPE_CLOSE_PRESENT';v=$js.Contains('handleKeydown')},
 @{n='NO_HORIZONTAL_OVERFLOW_GUARD_PRESENT';v=($styles.Contains('overflow-x:hidden') -and $styles.Contains('min-width:0'))},
 @{n='GET_ONLY_EVENT_DELEGATION_RETAINED';v=$js.Contains('window.__PWF_COMMAND_CENTER_UI_BOUND__')},
 @{n='NO_TIMER_LOOP';v=(-not ($js -match 'setInterval\s*\(|setTimeout\s*\(|requestAnimationFrame\s*\('))}
)
$fail=@($checks|Where-Object{-not $_.v});$checks|ForEach-Object{"$($_.n)=$($_.v)"};"STATIC_EVAL_FAILURE_COUNT=$($fail.Count)";'COMMAND_CENTER_GET_ONLY_CONTRACT=UNCHANGED';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';if($fail.Count){throw 'STATIC_EVAL_FAILED'};'STATIC_EVAL_RESULT=PASS'
