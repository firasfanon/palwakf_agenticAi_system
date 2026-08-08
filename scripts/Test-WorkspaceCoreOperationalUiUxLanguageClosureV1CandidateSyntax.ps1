[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@(
  'backend\src\palwakf_local_agents\workspace_core\static\index.html',
  'backend\src\palwakf_local_agents\workspace_core\static\styles.css',
  'backend\src\palwakf_local_agents\workspace_core\static\app.js',
  'backend\tests\test_workspace_core.py',
  'docs\WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1_AR.md',
  'docs\UAT_WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1_AR.md',
  'docs\CHANGELOG_WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1.md',
  'scripts\Test-WorkspaceCoreOperationalUiUxLanguageClosureV1Preflight.ps1',
  'scripts\Install-WorkspaceCoreOperationalUiUxLanguageClosureV1.ps1',
  'scripts\Test-WorkspaceCoreOperationalUiUxLanguageClosureV1Static.ps1'
)
$missing=@($required | Where-Object { -not (Test-Path (Join-Path $PackageRoot $_) -PathType Leaf) })
"REQUIRED_FILE_COUNT=$($required.Count)";"MISSING_FILE_COUNT=$($missing.Count)";"MISSING_FILES=$($missing -join ';')"
if($missing.Count){throw 'CANDIDATE_REQUIRED_FILES_MISSING'}
$python=(Get-Command python -ErrorAction SilentlyContinue)
if($null -eq $python){$python=(Get-Command py -ErrorAction Stop)}
$pyFiles=@(Get-ChildItem (Join-Path $PackageRoot 'backend') -Filter '*.py' -Recurse | Select-Object -ExpandProperty FullName)
if($pyFiles.Count -eq 0){throw 'PYTHON_FILES_MISSING_FOR_SYNTAX_GATE'}
& $python.Source -m py_compile @pyFiles
if($LASTEXITCODE -ne 0){throw 'PYTHON_COMPILE_FAILED'}
$node=Get-Command node -ErrorAction Stop
& $node.Source --check (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\workspace_core\static\app.js')
if($LASTEXITCODE -ne 0){throw 'NODE_CHECK_FAILED'}
$script=Get-Content (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\workspace_core\static\app.js') -Raw -Encoding UTF8
$styles=Get-Content (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\workspace_core\static\styles.css') -Raw -Encoding UTF8
$requiredMarkers=@('WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1','workspaceLabels','formatValue','tech-details','bindOnce')
$markerFailures=@($requiredMarkers | Where-Object {$script -notmatch [regex]::Escape($_)})
$styleMarkers=@('overflow-wrap:anywhere','word-break:break-word','@media(max-width:820px)')
$styleFailures=@($styleMarkers | Where-Object {$styles -notmatch [regex]::Escape($_)})
"UI_MARKER_FAILURE_COUNT=$($markerFailures.Count)";"UI_MARKER_FAILURES=$($markerFailures -join ';')"
"STYLE_MARKER_FAILURE_COUNT=$($styleFailures.Count)";"STYLE_MARKER_FAILURES=$($styleFailures -join ';')"
if($markerFailures.Count -or $styleFailures.Count){throw 'UI_OR_STYLE_CONTRACT_MARKERS_MISSING'}
foreach($disallowed in @('setInterval(','setTimeout(','requestAnimationFrame(')){if($script.Contains($disallowed)){throw "DISALLOWED_UI_LOOP_MARKER=$disallowed"}}
"CANDIDATE_SCOPE=WORKSPACE_CORE_UI_ASSETS_TESTS_AND_DOCS_ONLY"
"APP_ENTRYPOINT_MUTATION=NONE";"CORE_API_MUTATION=NONE";"POLICY_PACK_MUTATION=NONE";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED";"SYNTAX_GATE_RESULT=PASS"
