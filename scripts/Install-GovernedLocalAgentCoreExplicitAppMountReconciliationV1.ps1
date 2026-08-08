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
function Get-RegexCount([string]$Text, [string]$Pattern) { return [regex]::Matches($Text, $Pattern).Count }
function Assert-ExactSourcePostimage([string]$ProjectRoot, $SourceManifest) {
  foreach ($property in $SourceManifest.psobject.Properties) {
    $targetFile = Join-Path $ProjectRoot $property.Name.Replace("/", "\")
    if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) { throw "LOCAL_AGENT_CORE_SOURCE_MISSING=$($property.Name)" }
    if ((Get-Sha256 $targetFile) -ne $property.Value) { throw "LOCAL_AGENT_CORE_SOURCE_HASH_CONFLICT=$($property.Name)" }
  }
}

$batch = "GOVERNED_LOCAL_AGENT_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1"
# True WhatIf is permitted without -Apply. Actual writes still require -Apply.
if (-not $Apply -and -not $WhatIfPreference) { throw "APPLY_SWITCH_REQUIRED" }
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) { throw "PREFLIGHT_MANIFEST_NOT_FOUND=$PreflightManifest" }

$preflight = Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($preflight.batch -ne $batch) { throw "PREFLIGHT_BATCH_MISMATCH" }
if ($preflight.project_root -ne $ProjectRoot) { throw "PREFLIGHT_PROJECT_ROOT_MISMATCH" }
if ($preflight.source_state -ne "ALREADY_POSTIMAGE_UNMOUNTED") { throw "PREFLIGHT_SOURCE_STATE_MISMATCH=$($preflight.source_state)" }

$appPath = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
$sourceManifestPath = Join-Path $PackageRoot "CANDIDATE_SOURCE_POSTIMAGE_SHA256.json"
$anchorsPath = Join-Path $PackageRoot "EXPECTED_APP_ANCHORS.json"
foreach ($path in @($appPath, $sourceManifestPath, $anchorsPath)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "REQUIRED_PATH_NOT_FOUND=$path" }
}
if ((Get-Sha256 $appPath) -ne $preflight.app_preimage_sha256) { throw "APP_PREIMAGE_CHANGED_SINCE_PREFLIGHT" }

$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$anchors = Get-Content -LiteralPath $anchorsPath -Raw -Encoding UTF8 | ConvertFrom-Json
Assert-ExactSourcePostimage $ProjectRoot $sourceManifest

$appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$workspaceImport = Get-RegexCount $appText ([regex]::Escape([string]$anchors.workspace_import))
$workspaceMount = Get-RegexCount $appText ([regex]::Escape([string]$anchors.workspace_mount))
$localImport = Get-RegexCount $appText ([regex]::Escape([string]$anchors.local_agent_import))
$localMount = Get-RegexCount $appText ([regex]::Escape([string]$anchors.local_agent_mount))
if ($workspaceImport -ne 1 -or $workspaceMount -ne 1) { throw "WORKSPACE_CORE_ANCHORS_INVALID=$workspaceImport/$workspaceMount" }
if ($localImport -ne 0 -or $localMount -ne 0) { throw "LOCAL_AGENT_CORE_ANCHORS_NOT_CLEAN=$localImport/$localMount" }

function Get-TextSha256([string]$Text) {
  $encoding = [System.Text.UTF8Encoding]::new($false)
  $bytes = $encoding.GetBytes($Text)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "") }
  finally { $sha.Dispose() }
}

if ($WhatIfPreference) {
  $newline = if ($appText.Contains("`r`n")) { "`r`n" } else { "`n" }
  $replacementImport = ([string]$anchors.workspace_import) + $newline + ([string]$anchors.local_agent_import)
  $replacementMount = ([string]$anchors.workspace_mount) + $newline + ([string]$anchors.local_agent_mount)
  $predictedText = $appText.Replace([string]$anchors.workspace_import, $replacementImport)
  $predictedText = $predictedText.Replace([string]$anchors.workspace_mount, $replacementMount)
  $predictedWorkspaceImport = Get-RegexCount $predictedText ([regex]::Escape([string]$anchors.workspace_import))
  $predictedWorkspaceMount = Get-RegexCount $predictedText ([regex]::Escape([string]$anchors.workspace_mount))
  $predictedLocalImport = Get-RegexCount $predictedText ([regex]::Escape([string]$anchors.local_agent_import))
  $predictedLocalMount = Get-RegexCount $predictedText ([regex]::Escape([string]$anchors.local_agent_mount))
  if ($predictedWorkspaceImport -ne 1 -or $predictedWorkspaceMount -ne 1 -or $predictedLocalImport -ne 1 -or $predictedLocalMount -ne 1) {
    throw "WHATIF_PREDICTED_APP_ANCHOR_COUNTS_INVALID=$predictedWorkspaceImport/$predictedWorkspaceMount/$predictedLocalImport/$predictedLocalMount"
  }
  "INSTALL_STATUS=WHATIF_COMPLETE"
  "WHATIF_MODE=TRUE"
  "APPLY_SWITCH=NOT_REQUIRED_FOR_WHATIF"
  "APP_PREIMAGE_SHA256=$(Get-Sha256 $appPath)"
  "APP_POSTIMAGE_SHA256_PREDICTED=$(Get-TextSha256 $predictedText)"
  "PREDICTED_WORKSPACE_CORE_IMPORT_COUNT=$predictedWorkspaceImport"
  "PREDICTED_WORKSPACE_CORE_MOUNT_COUNT=$predictedWorkspaceMount"
  "PREDICTED_LOCAL_AGENT_CORE_IMPORT_COUNT=$predictedLocalImport"
  "PREDICTED_LOCAL_AGENT_CORE_MOUNT_COUNT=$predictedLocalMount"
  "TARGET_MUTATION_SCOPE=APP_PY_ONLY"
  "APP_ENTRYPOINT_MUTATION=EXPLICIT_LOCAL_AGENT_CORE_IMPORT_AND_MOUNT_ONLY"
  "LOCAL_AGENT_CORE_SOURCE_MUTATION=NONE"
  "WORKSPACE_CORE_MUTATION=NONE"
  "GOVERNED_OPERATIONS_MUTATION=NONE"
  "COMMAND_CENTER_MUTATION=NONE"
  "POLICY_PACK_MUTATION=NONE"
  "LOCAL_SQLITE_WRITE=NONE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  return
}

if (-not $PSCmdlet.ShouldProcess($appPath, "Add exact local_agent_core import and mount")) { return }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $ProjectRoot "backups\governed_local_agent_core_explicit_app_mount_reconciliation_v1_$stamp"
$backupApp = Join-Path $backup "backend\src\palwakf_local_agents\app.py"
New-Item -ItemType Directory -Path (Split-Path -Parent $backupApp) -Force | Out-Null
[System.IO.File]::Copy($appPath, $backupApp, $true)
$backupManifestPath = Join-Path $backup "install_preimage_manifest.json"
[ordered]@{
  backup_created_at = (Get-Date).ToUniversalTime().ToString("o")
  app_preimage_sha256 = Get-Sha256 $appPath
  preflight_manifest = $PreflightManifest
  source_state = $preflight.source_state
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $backupManifestPath -Encoding UTF8

$newline = if ($appText.Contains("`r`n")) { "`r`n" } else { "`n" }
$replacementImport = ([string]$anchors.workspace_import) + $newline + ([string]$anchors.local_agent_import)
$replacementMount = ([string]$anchors.workspace_mount) + $newline + ([string]$anchors.local_agent_mount)
$appText = $appText.Replace([string]$anchors.workspace_import, $replacementImport)
$appText = $appText.Replace([string]$anchors.workspace_mount, $replacementMount)
[System.IO.File]::WriteAllText($appPath, $appText, [System.Text.UTF8Encoding]::new($false))

$postText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$postWorkspaceImport = Get-RegexCount $postText ([regex]::Escape([string]$anchors.workspace_import))
$postWorkspaceMount = Get-RegexCount $postText ([regex]::Escape([string]$anchors.workspace_mount))
$postLocalImport = Get-RegexCount $postText ([regex]::Escape([string]$anchors.local_agent_import))
$postLocalMount = Get-RegexCount $postText ([regex]::Escape([string]$anchors.local_agent_mount))
if ($postWorkspaceImport -ne 1 -or $postWorkspaceMount -ne 1 -or $postLocalImport -ne 1 -or $postLocalMount -ne 1) {
  throw "POST_APPLY_APP_ANCHOR_COUNTS_INVALID=$postWorkspaceImport/$postWorkspaceMount/$postLocalImport/$postLocalMount"
}

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "PROJECT_VENV_PYTHON_NOT_FOUND=$python" }
$src = Join-Path $ProjectRoot "backend\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
& $python -c @"
from pathlib import Path
import ast
app = Path(r'$appPath')
root = Path(r'$src') / 'palwakf_local_agents' / 'local_agent_core'
ast.parse(app.read_text(encoding='utf-8'))
for item in sorted(root.rglob('*.py')):
    ast.parse(item.read_text(encoding='utf-8'))
print('POST_APPLY_PYTHON_AST_PARSE=PASS')
"@
if ($LASTEXITCODE -ne 0) { throw "POST_APPLY_AST_PARSE_FAILED" }

"INSTALL_STATUS=COMPLETE"
"BACKUP_PATH=$backup"
"BACKUP_MANIFEST_PATH=$backupManifestPath"
"APP_PREIMAGE_SHA256=$($preflight.app_preimage_sha256)"
"APP_POSTIMAGE_SHA256=$(Get-Sha256 $appPath)"
"TARGET_MUTATION_SCOPE=APP_PY_ONLY"
"APP_ENTRYPOINT_MUTATION=EXPLICIT_LOCAL_AGENT_CORE_IMPORT_AND_MOUNT_ONLY"
"LOCAL_AGENT_CORE_SOURCE_MUTATION=NONE"
"WORKSPACE_CORE_MUTATION=NONE"
"GOVERNED_OPERATIONS_MUTATION=NONE"
"COMMAND_CENTER_MUTATION=NONE"
"POLICY_PACK_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
