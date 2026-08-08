[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }

$appPath = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
$workspaceAnchorPath = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\workspace_core\__init__.py"
$manifestPath = Join-Path $PackageRoot "CANDIDATE_POSTIMAGE_SHA256.json"
if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) { throw "APP_ENTRYPOINT_NOT_FOUND=$appPath" }
if (-not (Test-Path -LiteralPath $workspaceAnchorPath -PathType Leaf)) { throw "WORKSPACE_CORE_PREREQUISITE_NOT_FOUND=$workspaceAnchorPath" }
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "CANDIDATE_HASH_MANIFEST_NOT_FOUND=$manifestPath" }

$hashManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = @(); $states = @()
foreach ($property in $hashManifest.psobject.Properties) {
  if (-not $property.Name.StartsWith("backend/")) { continue }
  $relative = $property.Name.Replace("/", "\")
  $candidateFile = Join-Path $PackageRoot $relative
  $targetFile = Join-Path $ProjectRoot $relative
  if (-not (Test-Path -LiteralPath $candidateFile -PathType Leaf)) { $failures += "CANDIDATE_FILE_MISSING=$relative"; continue }
  $candidateHash = Get-Sha256 $candidateFile
  if ($candidateHash -ne $property.Value) { $failures += "CANDIDATE_HASH_MISMATCH=$relative"; continue }
  if (Test-Path -LiteralPath $targetFile -PathType Leaf) {
    $targetHash = Get-Sha256 $targetFile
    $states += [pscustomobject]@{ RelativePath=$relative; State=$(if ($targetHash -eq $candidateHash) { "TARGET_EQUALS_POSTIMAGE" } else { "TARGET_CONFLICT" }) }
  } else {
    $states += [pscustomobject]@{ RelativePath=$relative; State="TARGET_MISSING_NEW_FILE" }
  }
}

$appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$workspaceImport = [regex]::Matches($appText, 'from \.workspace_core import mount_workspace_core').Count
$workspaceMount = [regex]::Matches($appText, 'mount_workspace_core\(app, project_root=PROJECT_ROOT\)').Count
$coreImport = [regex]::Matches($appText, 'from \.local_agent_core import mount_local_agent_core').Count
$coreMount = [regex]::Matches($appText, 'mount_local_agent_core\(app, project_root=PROJECT_ROOT\)').Count
if ($workspaceImport -ne 1) { $failures += "WORKSPACE_CORE_IMPORT_ANCHOR_COUNT=$workspaceImport" }
if ($workspaceMount -ne 1) { $failures += "WORKSPACE_CORE_MOUNT_ANCHOR_COUNT=$workspaceMount" }

$stateGroups = $states | Group-Object State
$allMissing = ($states.Count -gt 0 -and (@($states | Where-Object { $_.State -ne "TARGET_MISSING_NEW_FILE" }).Count -eq 0))
$allPostimage = ($states.Count -gt 0 -and (@($states | Where-Object { $_.State -ne "TARGET_EQUALS_POSTIMAGE" }).Count -eq 0))
if (-not $allMissing -and -not ($allPostimage -and $coreImport -eq 1 -and $coreMount -eq 1)) { $failures += "TARGET_SOURCE_STATE_NOT_CLEAN_OR_RECONCILED" }
if ($allMissing -and ($coreImport -ne 0 -or $coreMount -ne 0)) { $failures += "LOCAL_AGENT_CORE_APP_ANCHORS_UNEXPECTED=$coreImport/$coreMount" }
if ($allPostimage -and ($coreImport -ne 1 -or $coreMount -ne 1)) { $failures += "LOCAL_AGENT_CORE_RECONCILED_APP_ANCHORS_INVALID=$coreImport/$coreMount" }

"===== GOVERNED LOCAL AGENT CORE V1 PREFLIGHT ====="
$states | Format-Table RelativePath, State -AutoSize
"WORKSPACE_CORE_IMPORT_COUNT=$workspaceImport"
"WORKSPACE_CORE_MOUNT_COUNT=$workspaceMount"
"LOCAL_AGENT_CORE_IMPORT_COUNT=$coreImport"
"LOCAL_AGENT_CORE_MOUNT_COUNT=$coreMount"
"PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
if ($failures.Count -gt 0) { "PREFLIGHT_FAILURES=$($failures -join ';')"; throw "PREFLIGHT_FAILED" }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$evidenceRoot = Join-Path $env:TEMP "governed_local_agent_core_v1_preflight_$stamp"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$preflightManifest = [ordered]@{
  batch = "MEGA_BATCH_LOCAL_AGENTS_GOVERNED_LOCAL_AGENT_CORE_V1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  project_root = $ProjectRoot
  package_root = $PackageRoot
  app_preimage_sha256 = Get-Sha256 $appPath
  source_state = $(if ($allPostimage) { "ALREADY_POSTIMAGE" } else { "CLEAN_NEW_MODULE" })
  app_anchors = @{ workspace_import=$workspaceImport; workspace_mount=$workspaceMount; local_agent_import=$coreImport; local_agent_mount=$coreMount }
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
