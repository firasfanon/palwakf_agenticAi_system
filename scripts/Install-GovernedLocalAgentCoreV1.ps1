[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "High")]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$PreflightManifest,
  [ValidateSet("Upgrade")][string]$Mode = "Upgrade",
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Copy-Exact([string]$Source, [string]$Destination) { New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null; Copy-Item -LiteralPath $Source -Destination $Destination -Force }

if (-not $Apply) { throw "APPLY_SWITCH_REQUIRED" }
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) { throw "PREFLIGHT_MANIFEST_NOT_FOUND=$PreflightManifest" }
$preflight = Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($preflight.batch -ne "MEGA_BATCH_LOCAL_AGENTS_GOVERNED_LOCAL_AGENT_CORE_V1") { throw "PREFLIGHT_BATCH_MISMATCH" }
if ($preflight.project_root -ne $ProjectRoot) { throw "PREFLIGHT_PROJECT_ROOT_MISMATCH" }

$appPath = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
if ((Get-Sha256 $appPath) -ne $preflight.app_preimage_sha256 -and $preflight.source_state -ne "ALREADY_POSTIMAGE") { throw "APP_PREIMAGE_CHANGED_SINCE_PREFLIGHT" }
$hashManifestPath = Join-Path $PackageRoot "CANDIDATE_POSTIMAGE_SHA256.json"
$hashManifest = Get-Content -LiteralPath $hashManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in $hashManifest.psobject.Properties) {
  if (-not $property.Name.StartsWith("backend/")) { continue }
  $candidateFile = Join-Path $PackageRoot $property.Name.Replace("/", "\")
  if (-not (Test-Path -LiteralPath $candidateFile -PathType Leaf)) { throw "CANDIDATE_FILE_MISSING=$($property.Name)" }
  if ((Get-Sha256 $candidateFile) -ne $property.Value) { throw "CANDIDATE_HASH_MISMATCH=$($property.Name)" }
}

if ($WhatIfPreference) {
  "INSTALL_STATUS=WHATIF_COMPLETE"
  "TARGET_MUTATION_SCOPE=LOCAL_AGENT_CORE_MODULE_TEST_AND_ONE_APP_MOUNT"
  "PROJECT_MUTATION=NONE"
  "LOCAL_SQLITE_WRITE=NONE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  return
}

if ($preflight.source_state -eq "ALREADY_POSTIMAGE") {
  "INSTALL_STATUS=RECONCILED_ALREADY_POSTIMAGE"
  "PROJECT_MUTATION=NONE"
  "LOCAL_SQLITE_WRITE=NONE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  return
}

if (-not $PSCmdlet.ShouldProcess($ProjectRoot, "Apply Governed Local Agent Core V1")) { return }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $ProjectRoot "backups\governed_local_agent_core_v1_$stamp"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Exact $appPath (Join-Path $backup "backend\src\palwakf_local_agents\app.py")
[ordered]@{ backup_created_at=(Get-Date).ToUniversalTime().ToString("o"); app_preimage_sha256=(Get-Sha256 $appPath); preflight_manifest=$PreflightManifest } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backup "install_preimage_manifest.json") -Encoding UTF8

foreach ($property in $hashManifest.psobject.Properties) {
  if (-not $property.Name.StartsWith("backend/")) { continue }
  $relative = $property.Name.Replace("/", "\")
  Copy-Exact (Join-Path $PackageRoot $relative) (Join-Path $ProjectRoot $relative)
}

$appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$importAnchor = "from .workspace_core import mount_workspace_core"
$mountAnchor = "mount_workspace_core(app, project_root=PROJECT_ROOT)"
if ($appText.IndexOf($importAnchor) -lt 0 -or $appText.IndexOf($mountAnchor) -lt 0) { throw "APP_ANCHOR_NOT_FOUND_DURING_APPLY" }
$appText = $appText.Replace($importAnchor, "$importAnchor`r`nfrom .local_agent_core import mount_local_agent_core")
$appText = $appText.Replace($mountAnchor, "$mountAnchor`r`nmount_local_agent_core(app, project_root=PROJECT_ROOT)")
[System.IO.File]::WriteAllText($appPath, $appText, [System.Text.UTF8Encoding]::new($false))

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "PROJECT_VENV_PYTHON_NOT_FOUND=$python" }
$src = Join-Path $ProjectRoot "backend\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
& $python -c @"
from pathlib import Path
import ast
root = Path(r'$src') / 'palwakf_local_agents' / 'local_agent_core'
for item in sorted(root.rglob('*.py')):
    ast.parse(item.read_text(encoding='utf-8'))
ast.parse(Path(r'$appPath').read_text(encoding='utf-8'))
print('POST_APPLY_PYTHON_AST_PARSE=PASS')
"@
if ($LASTEXITCODE -ne 0) { throw "POST_APPLY_AST_PARSE_FAILED" }

"INSTALL_STATUS=COMPLETE"
"BACKUP_PATH=$backup"
"BACKUP_MANIFEST_PATH=$(Join-Path $backup 'install_preimage_manifest.json')"
"TARGET_MUTATION_SCOPE=LOCAL_AGENT_CORE_MODULE_TEST_AND_ONE_APP_MOUNT"
"APP_ENTRYPOINT_MUTATION=EXPLICIT_LOCAL_AGENT_CORE_IMPORT_AND_MOUNT_ONLY"
"WORKSPACE_CORE_MUTATION=NONE"
"GOVERNED_OPERATIONS_MUTATION=NONE"
"COMMAND_CENTER_MUTATION=NONE"
"POLICY_PACK_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
