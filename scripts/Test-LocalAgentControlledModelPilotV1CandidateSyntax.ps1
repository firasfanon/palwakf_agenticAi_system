[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$PackageRoot
)
$ErrorActionPreference = "Stop"
$required = @(
  "MANIFEST_LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1.md",
  "VALIDATION_REPORT_LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1.md",
  "APPLY_GUIDE_LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1_AR.md",
  "CANDIDATE_SOURCE_HASHES.json",
  "backend\src\palwakf_local_agents\local_agent_core\contracts.py",
  "backend\src\palwakf_local_agents\local_agent_core\policy.py",
  "backend\src\palwakf_local_agents\local_agent_core\router.py",
  "backend\src\palwakf_local_agents\local_agent_core\store.py",
  "backend\src\palwakf_local_agents\local_agent_core\model_pilot.py",
  "backend\tests\test_governed_local_agent_core.py",
  "config\local_agent_model_pilot_v1.json",
  "scripts\Test-LocalAgentControlledModelPilotV1Preflight.ps1",
  "scripts\Install-LocalAgentControlledModelPilotV1.ps1"
)
foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "CANDIDATE_REQUIRED_FILE_MISSING=$relative" }
}
$errors = @()
Get-ChildItem -LiteralPath (Join-Path $PackageRoot "scripts") -Filter "*.ps1" -File | ForEach-Object {
  $tokens = $null; $parseErrors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors)
  if ($parseErrors.Count -gt 0) { $errors += $_.FullName }
}
if ($errors.Count -gt 0) { throw "CANDIDATE_POWERSHELL_PARSE_FAIL=$($errors -join ';')" }
$config = Get-Content -LiteralPath (Join-Path $PackageRoot "config\local_agent_model_pilot_v1.json") -Raw | ConvertFrom-Json
if ($config.enabled -ne $false -or $config.provider -ne "ollama_local_only" -or $config.external_network -ne "NONE") { throw "CANDIDATE_CONFIG_SECURITY_CONTRACT_FAIL" }
$pythonFiles = Get-ChildItem -LiteralPath (Join-Path $PackageRoot "backend") -Filter "*.py" -File -Recurse
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) { throw "PYTHON_NOT_FOUND_FOR_CANDIDATE_AST" }
$astScript = Join-Path $env:TEMP ("pilot_candidate_ast_" + [guid]::NewGuid().ToString("N") + ".py")
$lines = @("import ast", "from pathlib import Path")
foreach ($file in $pythonFiles) { $escaped = $file.FullName.Replace("'", "\\'"); $lines += "ast.parse(Path(r'$escaped').read_text(encoding='utf-8'))" }
$lines += "print('CANDIDATE_PYTHON_AST_PARSE=PASS')"
$lines | Set-Content -LiteralPath $astScript -Encoding UTF8
& $python.Path $astScript
if ($LASTEXITCODE -ne 0) { throw "CANDIDATE_PYTHON_AST_PARSE_FAIL" }
Remove-Item -LiteralPath $astScript -Force -ErrorAction SilentlyContinue
"CANDIDATE_PACKAGE_INVENTORY=PASS"
"CANDIDATE_POWERSHELL_PARSE=PASS"
"CANDIDATE_CONFIG_SECURITY_CONTRACT=PASS"
"CANDIDATE_SYNTAX_RESULT=PASS"
