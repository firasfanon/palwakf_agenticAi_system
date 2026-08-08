[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][string]$PreflightManifest,
  [ValidateSet('Upgrade')][string]$Mode = 'Upgrade',
  [switch]$Apply
)
$ErrorActionPreference = "Stop"
$hashes = Get-Content -LiteralPath (Join-Path $PackageRoot "CANDIDATE_SOURCE_HASHES.json") -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) { throw "PREFLIGHT_MANIFEST_NOT_FOUND" }
$preflight = Get-Content -LiteralPath $PreflightManifest -Raw | ConvertFrom-Json
if ($preflight.failure_count -ne 0) { throw "PREFLIGHT_MANIFEST_NOT_CLEAN" }
$changes = @($hashes.postimage.PSObject.Properties)
if ($WhatIfPreference) {
  "INSTALL_STATUS=WHATIF_COMPLETE"
  "WHATIF_MODE=TRUE"
  "APPLY_SWITCH=NOT_REQUIRED_FOR_WHATIF"
  "TARGET_MUTATION_SCOPE=LOCAL_AGENT_CORE_AND_PILOT_CONFIG_ONLY"
  "APP_ENTRYPOINT_MUTATION=NONE"
  "PREDICTED_FILE_WRITE_COUNT=$($changes.Count)"
  foreach ($item in $changes) { "POSTIMAGE_SHA256_PREDICTED:$($item.Name)=$($item.Value)" }
  "DEFAULT_PILOT_ENABLED=FALSE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  "PROJECT_MUTATION=NONE"
  return
}
if (-not $Apply) { throw "APPLY_SWITCH_REQUIRED" }
foreach ($property in $hashes.preimage.PSObject.Properties) {
  $target = Join-Path $ProjectRoot $property.Name
  if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "TARGET_PREIMAGE_MISSING=$($property.Name)" }
  $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if ($actual -ne $property.Value) { throw "TARGET_PREIMAGE_HASH_MISMATCH=$($property.Name)" }
}
$configTarget = Join-Path $ProjectRoot "config\local_agent_model_pilot_v1.json"
$modelModuleTarget = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\local_agent_core\model_pilot.py"
if (Test-Path -LiteralPath $configTarget) { throw "PILOT_CONFIG_ALREADY_EXISTS" }
if (Test-Path -LiteralPath $modelModuleTarget) { throw "MODEL_PILOT_MODULE_ALREADY_EXISTS" }
if (-not $PSCmdlet.ShouldProcess($ProjectRoot, "Install controlled local model pilot source and disabled configuration")) { return }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupRoot = Join-Path $ProjectRoot "backups\local_agent_controlled_model_pilot_v1_$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$manifestEntries = @()
foreach ($item in $changes) {
  $source = Join-Path $PackageRoot $item.Name
  $target = Join-Path $ProjectRoot $item.Name
  $backup = Join-Path $backupRoot $item.Name
  $existed = Test-Path -LiteralPath $target -PathType Leaf
  if ($existed) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
    Copy-Item -LiteralPath $target -Destination $backup -Force
  }
  New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
  Copy-Item -LiteralPath $source -Destination $target -Force
  $manifestEntries += [pscustomobject]@{ relative_path = $item.Name; existed_before = $existed; preimage_sha256 = if ($existed) { (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash } else { $null }; postimage_sha256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash }
}
$backupManifest = Join-Path $backupRoot "install_preimage_manifest.json"
@{ contract="LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1"; changes=$manifestEntries } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $backupManifest -Encoding UTF8
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Path }
$astFile = Join-Path $env:TEMP ("pilot_post_apply_ast_" + [guid]::NewGuid().ToString('N') + '.py')
$pyTargets = @($changes | Where-Object { $_.Name.EndsWith('.py') } | ForEach-Object { Join-Path $ProjectRoot $_.Name })
$pyLines = @('import ast','from pathlib import Path')
foreach ($file in $pyTargets) { $escaped=$file.Replace("'","\\'"); $pyLines += "ast.parse(Path(r'$escaped').read_text(encoding='utf-8'))" }
$pyLines += "print('POST_APPLY_PYTHON_AST_PARSE=PASS')"
$pyLines | Set-Content -LiteralPath $astFile -Encoding UTF8
& $python $astFile
if ($LASTEXITCODE -ne 0) { throw "POST_APPLY_PYTHON_AST_PARSE_FAIL" }
Remove-Item -LiteralPath $astFile -Force -ErrorAction SilentlyContinue
$config = Get-Content -LiteralPath $configTarget -Raw | ConvertFrom-Json
if ($config.enabled -ne $false -or $config.external_network -ne 'NONE' -or $config.provider -ne 'ollama_local_only') { throw "POST_APPLY_PILOT_CONFIG_SECURITY_CONTRACT_FAIL" }
"INSTALL_STATUS=COMPLETE"
"BACKUP_PATH=$backupRoot"
"BACKUP_MANIFEST_PATH=$backupManifest"
"TARGET_MUTATION_SCOPE=LOCAL_AGENT_CORE_AND_PILOT_CONFIG_ONLY"
"APP_ENTRYPOINT_MUTATION=NONE"
"DEFAULT_PILOT_ENABLED=FALSE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"TOOL_EXECUTION=NONE"
"EXTERNAL_NETWORK=NONE"
"PROJECT_MUTATION=APPLIED_WITHIN_DECLARED_SCOPE"
