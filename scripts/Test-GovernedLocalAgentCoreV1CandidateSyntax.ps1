[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$required = @(
  "backend\src\palwakf_local_agents\local_agent_core\__init__.py",
  "backend\src\palwakf_local_agents\local_agent_core\contracts.py",
  "backend\src\palwakf_local_agents\local_agent_core\registry.py",
  "backend\src\palwakf_local_agents\local_agent_core\policy.py",
  "backend\src\palwakf_local_agents\local_agent_core\engine.py",
  "backend\src\palwakf_local_agents\local_agent_core\store.py",
  "backend\src\palwakf_local_agents\local_agent_core\router.py",
  "backend\src\palwakf_local_agents\local_agent_core\static\app.js",
  "backend\tests\test_governed_local_agent_core.py",
  "scripts\Test-GovernedLocalAgentCoreV1CandidateSyntax.ps1",
  "scripts\Test-GovernedLocalAgentCoreV1Preflight.ps1",
  "scripts\Install-GovernedLocalAgentCoreV1.ps1"
)
foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "CANDIDATE_REQUIRED_FILE_MISSING=$relative" }
}

$parseFailures = @()
Get-ChildItem -LiteralPath (Join-Path $PackageRoot "scripts") -Filter "*.ps1" -File | ForEach-Object {
  $tokens = $null; $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors) | Out-Null
  foreach ($error in $errors) { $parseFailures += "$($_.Name):$($error.Extent.StartLineNumber):$($error.Message)" }
}
if ($parseFailures.Count -gt 0) {
  $parseFailures | ForEach-Object { "POWERSHELL_PARSE_ERROR=$_" }
  throw "CANDIDATE_POWERSHELL_PARSE_FAILED"
}

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "PROJECT_VENV_PYTHON_NOT_FOUND=$python" }
$sourceRoot = Join-Path $PackageRoot "backend\src"
$testPath = Join-Path $PackageRoot "backend\tests\test_governed_local_agent_core.py"
& $python -c @"
from pathlib import Path
import ast
root = Path(r'$sourceRoot') / 'palwakf_local_agents' / 'local_agent_core'
files = sorted(root.rglob('*.py')) + [Path(r'$testPath')]
for item in files:
    ast.parse(item.read_text(encoding='utf-8'))
print(f'PYTHON_AST_PARSE_FILE_COUNT={len(files)}')
"@

$node = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $node) { throw "NODE_NOT_FOUND_FOR_STATIC_JS_SYNTAX" }
& $node.Source --check (Join-Path $PackageRoot "backend\src\palwakf_local_agents\local_agent_core\static\app.js")
if ($LASTEXITCODE -ne 0) { throw "STATIC_APP_JS_SYNTAX_FAILED" }

$sourceText = Get-Content -LiteralPath (Join-Path $PackageRoot "backend\src\palwakf_local_agents\local_agent_core\router.py") -Raw -Encoding UTF8
foreach ($forbidden in @('"/execute"', '"/dispatch"', '"/model"', '"/shell"', '"/deploy"')) {
  if ($sourceText.Contains($forbidden)) { throw "FORBIDDEN_EXECUTION_ROUTE_LITERAL_PRESENT=$forbidden" }
}


$preflightScript = Join-Path $PackageRoot "scripts\Test-GovernedLocalAgentCoreV1Preflight.ps1"
$preflightText = Get-Content -LiteralPath $preflightScript -Raw -Encoding UTF8
$runtimeExpressionFailures = @()
if ($preflightText -match 'State=\(if\s*\(') { $runtimeExpressionFailures += "PREFLIGHT_RUNTIME_EXPRESSION_UNWRAPPED=State" }
if ($preflightText -match '(?m)^\s*source_state\s*=\s*if\s*\(') { $runtimeExpressionFailures += "PREFLIGHT_RUNTIME_EXPRESSION_UNWRAPPED=source_state" }
if ($runtimeExpressionFailures.Count -gt 0) {
  $runtimeExpressionFailures | ForEach-Object { "PREFLIGHT_RUNTIME_GUARD_FAILURE=$_" }
  throw "CANDIDATE_PREFLIGHT_RUNTIME_EXPRESSION_GUARD_FAILED"
}

$smokeRoot = Join-Path $env:TEMP ("governed_local_agent_core_v1_preflight_runtime_smoke_" + [guid]::NewGuid().ToString("N"))
$smokeEvidenceRoot = $null
try {
  $smokeApp = Join-Path $smokeRoot "backend\src\palwakf_local_agents\app.py"
  $smokeWorkspaceCore = Join-Path $smokeRoot "backend\src\palwakf_local_agents\workspace_core\__init__.py"
  New-Item -ItemType Directory -Path (Split-Path -Parent $smokeApp) -Force | Out-Null
  New-Item -ItemType Directory -Path (Split-Path -Parent $smokeWorkspaceCore) -Force | Out-Null
  @'
from .workspace_core import mount_workspace_core
PROJECT_ROOT = None
app = object()
mount_workspace_core(app, project_root=PROJECT_ROOT)
'@ | Set-Content -LiteralPath $smokeApp -Encoding UTF8
  Set-Content -LiteralPath $smokeWorkspaceCore -Value "# runtime smoke fixture" -Encoding UTF8

  $smokeOutput = @(& $preflightScript -PackageRoot $PackageRoot -ProjectRoot $smokeRoot)
  $smokeOutput | ForEach-Object { "PREFLIGHT_RUNTIME_SMOKE_OUTPUT=$_" }
  $manifestLine = @($smokeOutput | Where-Object { $_ -like 'PREFLIGHT_MANIFEST=*' } | Select-Object -First 1)
  if ($manifestLine.Count -eq 1) { $smokeEvidenceRoot = Split-Path -Parent ($manifestLine[0].Substring('PREFLIGHT_MANIFEST='.Length)) }
  if (-not ($smokeOutput -contains "PREFLIGHT_RESULT=PASS")) { throw "PREFLIGHT_RUNTIME_SMOKE_FAILED" }
}
finally {
  if ($smokeEvidenceRoot -and (Test-Path -LiteralPath $smokeEvidenceRoot)) { Remove-Item -LiteralPath $smokeEvidenceRoot -Recurse -Force }
  if (Test-Path -LiteralPath $smokeRoot) { Remove-Item -LiteralPath $smokeRoot -Recurse -Force }
}
"PREFLIGHT_RUNTIME_EXPRESSION_GUARD=PASS"
"PREFLIGHT_RUNTIME_SMOKE=PASS"

"CANDIDATE_POWERSHELL_PARSE=PASS"
"PYTHON_AST_PARSE=PASS"
"STATIC_APP_JS_SYNTAX=PASS"
"CANDIDATE_SYNTAX_RESULT=PASS"
"PROJECT_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
