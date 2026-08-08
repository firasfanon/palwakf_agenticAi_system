[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$required = @(
  "CANDIDATE_SOURCE_POSTIMAGE_SHA256.json",
  "EXPECTED_APP_ANCHORS.json",
  "MANIFEST_GOVERNED_LOCAL_AGENT_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_VALIDATION_PACKAGE_REPAIR.md",
  "APPLY_GUIDE_GOVERNED_LOCAL_AGENT_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_VALIDATION_PACKAGE_REPAIR_AR.md",
  "VALIDATION_REPORT_GOVERNED_LOCAL_AGENT_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_VALIDATION_PACKAGE_REPAIR.md",
  "scripts\Test-GovernedLocalAgentCoreExplicitAppMountReconciliationV1CandidateSyntax.ps1",
  "scripts\Test-GovernedLocalAgentCoreExplicitAppMountReconciliationV1Preflight.ps1",
  "scripts\Install-GovernedLocalAgentCoreExplicitAppMountReconciliationV1.ps1"
)
foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "CANDIDATE_REQUIRED_FILE_MISSING=$relative" }
}

$inventoryPath = Join-Path $PackageRoot "PACKAGE_FILE_INVENTORY_SHA256.json"
if (-not (Test-Path -LiteralPath $inventoryPath -PathType Leaf)) { throw "PACKAGE_FILE_INVENTORY_MISSING" }
$inventory = Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in $inventory.psobject.Properties) {
  $path = Join-Path $PackageRoot $property.Name.Replace("/", "\")
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "PACKAGE_INVENTORY_FILE_MISSING=$($property.Name)" }
  $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($actual -ne $property.Value) { throw "PACKAGE_INVENTORY_HASH_MISMATCH=$($property.Name)" }
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

$preflightPath = Join-Path $PackageRoot "scripts\Test-GovernedLocalAgentCoreExplicitAppMountReconciliationV1Preflight.ps1"
$installerPath = Join-Path $PackageRoot "scripts\Install-GovernedLocalAgentCoreExplicitAppMountReconciliationV1.ps1"
$preflightText = Get-Content -LiteralPath $preflightPath -Raw -Encoding UTF8
$installerText = Get-Content -LiteralPath $installerPath -Raw -Encoding UTF8
foreach ($forbidden in @('State=(if', 'source_state = if', 'Copy-Exact', 'Copy-Item -LiteralPath (Join-Path $PackageRoot')) {
  if ($preflightText.Contains($forbidden) -or $installerText.Contains($forbidden)) { throw "FORBIDDEN_OR_UNSAFE_PATTERN_PRESENT=$forbidden" }
}
if (-not $installerText.Contains('TARGET_MUTATION_SCOPE=APP_PY_ONLY')) { throw "INSTALLER_MUTATION_SCOPE_CONTRACT_MISSING" }
if (-not $installerText.Contains('LOCAL_AGENT_CORE_SOURCE_MUTATION=NONE')) { throw "INSTALLER_SOURCE_PRESERVATION_CONTRACT_MISSING" }
if (-not $installerText.Contains('if (-not $Apply -and -not $WhatIfPreference) { throw "APPLY_SWITCH_REQUIRED" }')) { throw "TRUE_WHATIF_GUARD_MISSING" }
if (-not $installerText.Contains('APPLY_SWITCH=NOT_REQUIRED_FOR_WHATIF')) { throw "TRUE_WHATIF_REPORT_CONTRACT_MISSING" }
if (-not $installerText.Contains('APP_POSTIMAGE_SHA256_PREDICTED=')) { throw "WHATIF_PREDICTED_HASH_CONTRACT_MISSING" }

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "PROJECT_VENV_PYTHON_NOT_FOUND=$python" }
$app = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
$localAgentRoot = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\local_agent_core"
if (-not (Test-Path -LiteralPath $app -PathType Leaf)) { throw "APP_ENTRYPOINT_NOT_FOUND=$app" }
if (-not (Test-Path -LiteralPath $localAgentRoot -PathType Container)) { throw "LOCAL_AGENT_CORE_SOURCE_NOT_FOUND=$localAgentRoot" }
& $python -c @"
from pathlib import Path
import ast
app = Path(r'$app')
root = Path(r'$localAgentRoot')
ast.parse(app.read_text(encoding='utf-8'))
files = sorted(root.rglob('*.py'))
for item in files:
    ast.parse(item.read_text(encoding='utf-8'))
print(f'PYTHON_AST_PARSE_FILE_COUNT={len(files)+1}')
"@
if ($LASTEXITCODE -ne 0) { throw "PYTHON_AST_PARSE_FAILED" }

"CANDIDATE_PACKAGE_INVENTORY=PASS"
"CANDIDATE_POWERSHELL_PARSE=PASS"
"PREVIOUS_PREFLIGHT_RUNTIME_DEFECT_GUARD=PASS"
"TRUE_WHATIF_GUARD=PASS"
"WHATIF_PREDICTED_HASH_CONTRACT=PASS"
"VALIDATION_DOCUMENT_CONTRACT=PASS"
"PYTHON_AST_PARSE=PASS"
"CANDIDATE_SYNTAX_RESULT=PASS"
"PROJECT_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
