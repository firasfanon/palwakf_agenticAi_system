
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$AppJsPath)
$ErrorActionPreference="Stop"
if(-not(Test-Path -LiteralPath $AppJsPath -PathType Leaf)){throw "APP_JS_NOT_FOUND=$AppJsPath"}
$node=Get-Command node -ErrorAction Stop
& $node.Source --check $AppJsPath
if($LASTEXITCODE -ne 0){throw "APP_JS_NODE_CHECK_FAILED"}
$text=Get-Content -LiteralPath $AppJsPath -Raw -Encoding UTF8
function CountLiteral([string]$needle){return ([regex]::Matches($text,[regex]::Escape($needle))).Count}
$checks=@{
  'FUNCTION_WIRE_ABSENT' = (CountLiteral 'function wire()') -eq 0
  'RENDER_WIRE_CALL_ABSENT' = (CountLiteral 'wire()}catch') -eq 0
  'DOCUMENT_CLICK_HANDLER_ONCE' = (CountLiteral 'document.addEventListener("click",handleDocumentClick)') -eq 1
  'POPSTATE_HANDLER_ONCE' = (CountLiteral 'addEventListener("popstate",render)') -eq 1
  'BOOTSTRAP_GUARD_PRESENT' = (CountLiteral 'window.__PWF_COMMAND_CENTER_UI_BOUND__') -ge 2
  'BOOTSTRAP_BIND_AND_RENDER_PRESENT' = (CountLiteral 'bindUiOnce();render()') -eq 1
  'NO_INTERVAL_TIMER' = (CountLiteral 'setInterval') -eq 0
  'NO_TIMEOUT_TIMER' = (CountLiteral 'setTimeout') -eq 0
  'NO_RAF_TIMER' = (CountLiteral 'requestAnimationFrame') -eq 0
}
$fail=0
foreach($key in $checks.Keys){"$key=$($checks[$key] -eq $true)";if(-not $checks[$key]){$fail++}}
"STATIC_EVAL_FAILURE_COUNT=$fail"
"EVENT_LISTENER_DEDUPLICATION=BOOTSTRAP_ONCE_EVENT_DELEGATION"
"TIMER_DRIVEN_RERENDER=ABSENT"
if($fail){throw "STATIC_EVAL_FAILED"}
"STATIC_EVAL_RESULT=PASS"
