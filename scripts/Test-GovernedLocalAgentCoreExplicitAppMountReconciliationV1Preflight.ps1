[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Get-RegexCount([string]$Text, [string]$Pattern) { return [regex]::Matches($Text, $Pattern).Count }

$batch = "GOVERNED_LOCAL_AGENT_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1"
$appPath = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
$sourceManifestPath = Join-Path $PackageRoot "CANDIDATE_SOURCE_POSTIMAGE_SHA256.json"
$anchorsPath = Join-Path $PackageRoot "EXPECTED_APP_ANCHORS.json"

foreach ($path in @($appPath, $sourceManifestPath, $anchorsPath)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "REQUIRED_PATH_NOT_FOUND=$path" }
}

$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$anchors = Get-Content -LiteralPath $anchorsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = @()
$states = @()

foreach ($property in $sourceManifest.psobject.Properties) {
  $relative = $property.Name.Replace("/", "\")
  $targetFile = Join-Path $ProjectRoot $relative
  if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) {
    $states += [pscustomobject]@{ RelativePath = $relative; State = "TARGET_MISSING" }
    $failures += "LOCAL_AGENT_CORE_SOURCE_MISSING=$relative"
    continue
  }
  $actualHash = Get-Sha256 $targetFile
  if ($actualHash -eq $property.Value) {
    $states += [pscustomobject]@{ RelativePath = $relative; State = "TARGET_EQUALS_POSTIMAGE" }
  }
  else {
    $states += [pscustomobject]@{ RelativePath = $relative; State = "TARGET_HASH_CONFLICT" }
    $failures += "LOCAL_AGENT_CORE_SOURCE_HASH_CONFLICT=$relative"
  }
}

$appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$workspaceImport = Get-RegexCount $appText ([regex]::Escape([string]$anchors.workspace_import))
$workspaceMount = Get-RegexCount $appText ([regex]::Escape([string]$anchors.workspace_mount))
$localImport = Get-RegexCount $appText ([regex]::Escape([string]$anchors.local_agent_import))
$localMount = Get-RegexCount $appText ([regex]::Escape([string]$anchors.local_agent_mount))

if ($workspaceImport -ne 1) { $failures += "WORKSPACE_CORE_IMPORT_ANCHOR_COUNT=$workspaceImport" }
if ($workspaceMount -ne 1) { $failures += "WORKSPACE_CORE_MOUNT_ANCHOR_COUNT=$workspaceMount" }
if ($localImport -ne 0) { $failures += "LOCAL_AGENT_CORE_IMPORT_MUST_BE_ABSENT_BEFORE_RECONCILIATION=$localImport" }
if ($localMount -ne 0) { $failures += "LOCAL_AGENT_CORE_MOUNT_MUST_BE_ABSENT_BEFORE_RECONCILIATION=$localMount" }

$sourceExactCount = @($states | Where-Object { $_.State -eq "TARGET_EQUALS_POSTIMAGE" }).Count
if ($sourceExactCount -ne $states.Count) { $failures += "LOCAL_AGENT_CORE_SOURCE_POSTIMAGE_NOT_EXACT=$sourceExactCount/$($states.Count)" }

"===== GOVERNED LOCAL AGENT CORE EXPLICIT APP MOUNT RECONCILIATION V1 PREFLIGHT ====="
$states | Format-Table RelativePath, State -AutoSize
"LOCAL_AGENT_CORE_SOURCE_EXPECTED_COUNT=$($states.Count)"
"LOCAL_AGENT_CORE_SOURCE_EXACT_MATCH_COUNT=$sourceExactCount"
"WORKSPACE_CORE_IMPORT_COUNT=$workspaceImport"
"WORKSPACE_CORE_MOUNT_COUNT=$workspaceMount"
"LOCAL_AGENT_CORE_IMPORT_COUNT=$localImport"
"LOCAL_AGENT_CORE_MOUNT_COUNT=$localMount"
"PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
if ($failures.Count -gt 0) {
  "PREFLIGHT_FAILURES=$($failures -join ';')"
  throw "PREFLIGHT_FAILED"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$evidenceRoot = Join-Path $env:TEMP "governed_local_agent_core_explicit_app_mount_reconciliation_v1_preflight_$stamp"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$preflightManifest = [ordered]@{
  batch = $batch
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  project_root = $ProjectRoot
  package_root = $PackageRoot
  app_preimage_sha256 = Get-Sha256 $appPath
  source_state = "ALREADY_POSTIMAGE_UNMOUNTED"
  source_expected_count = $states.Count
  source_exact_match_count = $sourceExactCount
  app_anchors_before = @{ workspace_import=$workspaceImport; workspace_mount=$workspaceMount; local_agent_import=$localImport; local_agent_mount=$localMount }
}
$preflightManifestPath = Join-Path $evidenceRoot "preflight_preimage_manifest.json"
$preflightManifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $preflightManifestPath -Encoding UTF8
"PREFLIGHT_MANIFEST=$preflightManifestPath"
"PREFLIGHT_SOURCE_STATE=$($preflightManifest.source_state)"
"PREFLIGHT_RESULT=PASS"
"PROJECT_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
