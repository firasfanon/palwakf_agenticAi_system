[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][string]$PreflightManifest,
  [ValidateSet("Upgrade")][string]$Mode = "Upgrade",
  [switch]$Apply
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $PackageRoot -PathType Container)) { throw "PACKAGE_ROOT_NOT_FOUND" }
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "PROJECT_ROOT_NOT_FOUND" }
if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) { throw "PREFLIGHT_MANIFEST_NOT_FOUND" }

$preflight = Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($preflight.contract -ne "MEGA_BATCH_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_BOOTSTRAP_V1") { throw "PREFLIGHT_MANIFEST_CONTRACT_INVALID" }
if ([int]$preflight.failure_count -ne 0) { throw "PREFLIGHT_MANIFEST_NOT_CLEAN" }
if ([string]$preflight.project_root -ne [string]$ProjectRoot) { throw "PREFLIGHT_MANIFEST_PROJECT_ROOT_MISMATCH" }

if (-not $WhatIfPreference -and -not $Apply) { throw "APPLY_SWITCH_REQUIRED" }

$targets = @($preflight.bootstrap_targets)
if ($targets.Count -ne 3) { throw "PREFLIGHT_BOOTSTRAP_TARGET_COUNT_INVALID" }

foreach ($target in $targets) {
  if ([string]$target.State -ne "ABSENT_EXPECTED_PREIMAGE") { throw "PREFLIGHT_BOOTSTRAP_TARGET_NOT_ABSENT=$($target.WorkspaceId)" }
  $workspaceRoot = Join-Path $ProjectRoot ([string]$target.TargetRoot).Replace("/", "\\")
  if (Test-Path -LiteralPath $workspaceRoot) { throw "TARGET_WORKSPACE_ALREADY_EXISTS=$($target.WorkspaceId)" }
  $template = Join-Path $PackageRoot ("candidate\\bootstrap_manifests\\" + [string]$target.WorkspaceId + "\\workspace_manifest.json")
  if (-not (Test-Path -LiteralPath $template -PathType Leaf)) { throw "BOOTSTRAP_TEMPLATE_MISSING=$($target.WorkspaceId)" }
  $actualTemplateHash = (Get-FileHash -LiteralPath $template -Algorithm SHA256).Hash
  if ($actualTemplateHash -ne [string]$target.TemplateSHA256) { throw "BOOTSTRAP_TEMPLATE_HASH_MISMATCH=$($target.WorkspaceId)" }
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $ProjectRoot ("backups\\multi_workspace_agent_capability_expansion_v1_bootstrap_" + $stamp)

if ($WhatIfPreference) {
  "INSTALL_STATUS=WHATIF_COMPLETE"
  "WHATIF_MODE=TRUE"
  "APPLY_SWITCH=NOT_REQUIRED_FOR_WHATIF"
  "PREDICTED_WORKSPACE_ROOT_CREATION_COUNT=3"
  "PREDICTED_WORKSPACE_MANIFEST_WRITE_COUNT=3"
  "PREDICTED_LOCAL_SQLITE_WRITE_COUNT=0"
  "TARGET_MUTATION_SCOPE=THREE_NEW_WORKSPACE_ROOTS_AND_IDENTITY_MANIFESTS_ONLY"
  "APP_ENTRYPOINT_MUTATION=NONE"
  "LOCAL_AGENT_CORE_SOURCE_MUTATION=NONE"
  "WORKSPACE_CORE_SOURCE_MUTATION=NONE"
  "PALWAKF_GOVERNMENT_WORKSPACE_MUTATION=NONE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  "SHELL_EXECUTION=NONE"
  "GIT_WRITE=NONE"
  "PROJECT_FILE_WRITE=NONE_OUTSIDE_BOOTSTRAP_MANIFESTS"
  "DEPLOYMENT=NONE"
  "EXTERNAL_NETWORK=NONE"
  exit 0
}

if (-not $PSCmdlet.ShouldProcess($ProjectRoot, "Bootstrap three isolated workspace identity manifests")) {
  throw "BOOTSTRAP_OPERATION_DECLINED"
}

$createdRoots = @()
try {
  New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
  $backupManifestPath = Join-Path $backupPath "bootstrap_preimage_manifest.json"
  $backupManifest = [ordered]@{
    contract = "MEGA_BATCH_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_BOOTSTRAP_V1"
    created_at = (Get-Date).ToString("o")
    preflight_manifest = $PreflightManifest
    preimage = @($targets | ForEach-Object {
      [ordered]@{
        workspace_id = $_.WorkspaceId
        workspace_root = $_.TargetRoot
        workspace_root_state = "ABSENT_EXPECTED_PREIMAGE"
        workspace_manifest_state = "ABSENT_EXPECTED_PREIMAGE"
      }
    })
    rollback_scope = "REMOVE_ONLY_THE_THREE_NEW_WORKSPACE_ROOTS_IF_CREATED_BY_THIS_INSTALLER_AND_IF_NO_UNEXPECTED_CONTENT_EXISTS"
  }
  $backupManifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $backupManifestPath -Encoding UTF8

  foreach ($target in $targets) {
    $workspaceRoot = Join-Path $ProjectRoot ([string]$target.TargetRoot).Replace("/", "\\")
    $manifestTarget = Join-Path $ProjectRoot ([string]$target.TargetManifest).Replace("/", "\\")
    $template = Join-Path $PackageRoot ("candidate\\bootstrap_manifests\\" + [string]$target.WorkspaceId + "\\workspace_manifest.json")

    New-Item -ItemType Directory -Path $workspaceRoot -Force | Out-Null
    $createdRoots += $workspaceRoot
    Copy-Item -LiteralPath $template -Destination $manifestTarget -Force
  }
}
catch {
  foreach ($workspaceRoot in @($createdRoots | Sort-Object -Descending)) {
    if (Test-Path -LiteralPath $workspaceRoot -PathType Container) {
      Remove-Item -LiteralPath $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
  throw
}

$postFailures = @()
$postRows = @()
foreach ($target in $targets) {
  $workspaceRoot = Join-Path $ProjectRoot ([string]$target.TargetRoot).Replace("/", "\\")
  $manifestTarget = Join-Path $ProjectRoot ([string]$target.TargetManifest).Replace("/", "\\")
  $template = Join-Path $PackageRoot ("candidate\\bootstrap_manifests\\" + [string]$target.WorkspaceId + "\\workspace_manifest.json")
  $actualHash = (Get-FileHash -LiteralPath $manifestTarget -Algorithm SHA256).Hash
  $expectedHash = (Get-FileHash -LiteralPath $template -Algorithm SHA256).Hash
  $sqlitePaths = @(
    (Join-Path $workspaceRoot "state.sqlite"),
    (Join-Path $workspaceRoot "audit.sqlite"),
    (Join-Path $workspaceRoot "local_agent_core.sqlite")
  )
  $sqliteCreated = @($sqlitePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }).Count
  $postRows += [pscustomobject]@{
    WorkspaceId = [string]$target.WorkspaceId
    ManifestHash = $actualHash
    HashMatchesTemplate = ($actualHash -eq $expectedHash)
    SQLiteFilesCreated = $sqliteCreated
  }
  if ($actualHash -ne $expectedHash) { $postFailures += "POSTIMAGE_HASH_MISMATCH=$($target.WorkspaceId)" }
  if ($sqliteCreated -ne 0) { $postFailures += "BOOTSTRAP_SQLITE_WRITE_DETECTED=$($target.WorkspaceId)" }
}

if ($postFailures.Count -gt 0) {
  throw "BOOTSTRAP_POST_APPLY_VERIFICATION_FAILED=$($postFailures -join ';')"
}

"POST_APPLY_BOOTSTRAP_MANIFEST_HASHES=PASS"
"POST_APPLY_LOCAL_SQLITE_WRITE_COUNT=0"
"INSTALL_STATUS=COMPLETE"
"BACKUP_PATH=$backupPath"
"BACKUP_MANIFEST_PATH=$backupManifestPath"
"BOOTSTRAPPED_WORKSPACE_COUNT=3"
"BOOTSTRAPPED_WORKSPACES=personal_development,commercial_projects,research_learning"
"TARGET_MUTATION_SCOPE=THREE_NEW_WORKSPACE_ROOTS_AND_IDENTITY_MANIFESTS_ONLY_PLUS_BACKUP_MANIFEST"
"APP_ENTRYPOINT_MUTATION=NONE"
"LOCAL_AGENT_CORE_SOURCE_MUTATION=NONE"
"WORKSPACE_CORE_SOURCE_MUTATION=NONE"
"PALWAKF_GOVERNMENT_WORKSPACE_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"SHELL_EXECUTION=NONE"
"GIT_WRITE=NONE"
"PROJECT_FILE_WRITE=NONE_OUTSIDE_BOOTSTRAP_MANIFESTS"
"DEPLOYMENT=NONE"
"EXTERNAL_NETWORK=NONE"
