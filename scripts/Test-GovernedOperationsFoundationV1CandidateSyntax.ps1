[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot)
$ErrorActionPreference='Stop'
$p=(Resolve-Path -LiteralPath $PackageRoot).Path
$required=@(
 'backend\src\palwakf_local_agents\governed_operations\__init__.py',
 'backend\src\palwakf_local_agents\governed_operations\contracts.py',
 'backend\src\palwakf_local_agents\governed_operations\store.py',
 'backend\src\palwakf_local_agents\governed_operations\router.py',
 'backend\src\palwakf_local_agents\governed_operations\static\index.html',
 'backend\src\palwakf_local_agents\governed_operations\static\styles.css',
 'backend\src\palwakf_local_agents\governed_operations\static\app.js',
 'backend\tests\test_governed_operations.py',
 'scripts\Install-GovernedOperationsFoundationV1.ps1',
 'scripts\Test-GovernedOperationsFoundationV1Preflight.ps1',
 'docs\ARCHITECTURE_GOVERNED_OPERATIONS_FOUNDATION_V1_AR.md',
 'docs\SECURITY_CONTRACT_GOVERNED_OPERATIONS_FOUNDATION_V1.md',
 'MANIFEST_GOVERNED_OPERATIONS_FOUNDATION_V1.md'
)
$missing=@();foreach($r in $required){if(-not(Test-Path -LiteralPath (Join-Path $p $r) -PathType Leaf)){$missing+=$r}}
$pyFailures=@();Get-ChildItem -LiteralPath (Join-Path $p 'backend') -Recurse -Filter '*.py' -File | ForEach-Object { & python -m py_compile $_.FullName 2>$null; if($LASTEXITCODE -ne 0){$pyFailures+=$_.FullName} }
$js=Get-Content -LiteralPath (Join-Path $p 'backend\src\palwakf_local_agents\governed_operations\static\app.js') -Raw -Encoding UTF8
$contractFailures=@();foreach($needle in @('GOVERNED_OPERATIONS_LOCAL_ONLY','/api/v1/governed-operations','model_execution','pilot_execution')){if($js -notmatch [regex]::Escape($needle)){$contractFailures+=$needle}}
$forbidden=@();if($js -match '(?i)ollama|openai|anthropic|/execute|/run\b'){$forbidden+='MODEL_OR_EXECUTION_UI_REFERENCE'}
Write-Output "REQUIRED_FILE_COUNT=$($required.Count)";Write-Output "MISSING_FILE_COUNT=$($missing.Count)";Write-Output "PYTHON_COMPILE_FAILURE_COUNT=$($pyFailures.Count)";Write-Output "CONTRACT_MARKER_FAILURE_COUNT=$($contractFailures.Count)";Write-Output "FORBIDDEN_UI_PATTERN_COUNT=$($forbidden.Count)";Write-Output 'CANDIDATE_SCOPE=GOVERNED_OPERATIONS_LOCAL_STATE_HUMAN_REVIEW_EVIDENCE';Write-Output 'MODEL_EXECUTION=NONE';Write-Output 'PILOT_EXECUTION=NOT_EXECUTED';Write-Output 'PLATFORM_MUTATION=NONE';Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE';Write-Output 'LOCAL_PERSISTENT_STATE=SQLITE_ONLY'
if($missing.Count -or $pyFailures.Count -or $contractFailures.Count -or $forbidden.Count){Write-Output 'SYNTAX_GATE_RESULT=FAIL';exit 1};Write-Output 'SYNTAX_GATE_RESULT=PASS'
