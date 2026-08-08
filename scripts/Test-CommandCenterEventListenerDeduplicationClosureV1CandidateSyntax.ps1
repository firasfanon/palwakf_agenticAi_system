
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$PackageRoot)

$ErrorActionPreference = "Stop"
$js = Join-Path $PackageRoot "backend\src\palwakf_local_agents\command_center\static\app.js"
$required = @(
  $js,
  (Join-Path $PackageRoot "scripts\Test-CommandCenterEventListenerDeduplicationClosureV1Preflight.ps1"),
  (Join-Path $PackageRoot "scripts\Test-CommandCenterEventListenerDeduplicationClosureV1StaticEval.ps1"),
  (Join-Path $PackageRoot "scripts\Install-CommandCenterEventListenerDeduplicationClosureV1.ps1"),
  (Join-Path $PackageRoot "docs\README_COMMAND_CENTER_EVENT_LISTENER_DEDUPLICATION_CLOSURE_V1_AR.md"),
  (Join-Path $PackageRoot "docs\SECURITY_CONTRACT_COMMAND_CENTER_EVENT_LISTENER_DEDUPLICATION_CLOSURE_V1.md"),
  (Join-Path $PackageRoot "MANIFEST_COMMAND_CENTER_EVENT_LISTENER_DEDUPLICATION_CLOSURE_V1.md")
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
if($missing.Count){$missing|ForEach-Object{"MISSING_FILE=$_"};throw "CANDIDATE_REQUIRED_FILES_MISSING"}

$node = Get-Command node -ErrorAction Stop
& $node.Source --check $js
if($LASTEXITCODE -ne 0){throw "CANDIDATE_APP_JS_NODE_CHECK_FAILED"}

$text = Get-Content -LiteralPath $js -Raw -Encoding UTF8
$mustContain = @(
  'function handleDocumentClick(e)',
  'function bindUiOnce()',
  'window.__PWF_COMMAND_CENTER_UI_BOUND__',
  'document.addEventListener("click",handleDocumentClick)',
  'addEventListener("popstate",render)',
  'bindUiOnce();render()'
)
$forbidden = @(
  'function wire()',
  'wire()',
  'setInterval',
  'setTimeout',
  'requestAnimationFrame'
)
$fail=0
foreach($marker in $mustContain){if($text -notmatch [regex]::Escape($marker)){"MISSING_REQUIRED_MARKER=$marker";$fail++}}
foreach($marker in $forbidden){if($text -match [regex]::Escape($marker)){"FORBIDDEN_MARKER_PRESENT=$marker";$fail++}}
"CONTRACT_MARKER_FAILURE_COUNT=$fail"
"TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY"
"COMMAND_CENTER_EVENT_WIRING=BOOTSTRAP_ONCE_EVENT_DELEGATION"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
if($fail){throw "CANDIDATE_CONTRACT_VALIDATION_FAILED"}
"SYNTAX_GATE_RESULT=PASS"
