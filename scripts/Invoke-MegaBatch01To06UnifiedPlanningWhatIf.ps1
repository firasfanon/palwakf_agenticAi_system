[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][string]$PreflightManifest,
  [switch]$AllowPackageRuntimeSelfTest
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) {
  throw ("PREFLIGHT_MANIFEST_NOT_FOUND={0}" -f $PreflightManifest)
}

$contractPath = Join-Path $PackageRoot "contracts\master_batch_contract_v1.json"
$preflightScriptPath = Join-Path $PackageRoot "scripts\Invoke-MegaBatch01To06UnifiedBaselinePreflight.ps1"
foreach ($requiredPath in @($PackageRoot, $ProjectRoot, $contractPath, $preflightScriptPath)) {
  if (-not (Test-Path -LiteralPath $requiredPath)) {
    throw ("REQUIRED_PATH_NOT_FOUND={0}" -f $requiredPath)
  }
}

$contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$preflight = Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
$expectedPackageId = [string]$contract.package_id
$expectedSchemaVersion = [string]$contract.manifest_binding_schema_version
$expectedContractHash = (Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash
$expectedPreflightHash = (Get-FileHash -LiteralPath $preflightScriptPath -Algorithm SHA256).Hash
$expectedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

if ([string]$preflight.package_id -ne $expectedPackageId) {
  throw "PREFLIGHT_MANIFEST_PACKAGE_ID_MISMATCH"
}
if ([string]$preflight.manifest_binding_schema_version -ne $expectedSchemaVersion) {
  throw "PREFLIGHT_MANIFEST_SCHEMA_VERSION_MISMATCH"
}
if ([string]$preflight.contract_sha256 -ne $expectedContractHash) {
  throw "PREFLIGHT_MANIFEST_CONTRACT_HASH_MISMATCH"
}
if ([string]$preflight.preflight_script_sha256 -ne $expectedPreflightHash) {
  throw "PREFLIGHT_MANIFEST_PREFLIGHT_SCRIPT_HASH_MISMATCH"
}
if ([string]$preflight.project_root -ne $expectedProjectRoot) {
  throw "PREFLIGHT_MANIFEST_PROJECT_ROOT_MISMATCH"
}
if ([int]$preflight.preflight_failure_count -ne 0) {
  throw "PREFLIGHT_MANIFEST_NOT_CLEAN"
}
if (-not $AllowPackageRuntimeSelfTest -and [string]$preflight.baseline_hash_check -ne "PASS") {
  throw "PREFLIGHT_MANIFEST_BASELINE_HASH_CHECK_NOT_PASS"
}
if ([string]$preflight.government_sqlite_state -ne "PRESENT") {
  throw "GOVERNMENT_SQLITE_PREIMAGE_UNRECOGNIZED"
}
if (
  [string]$preflight.government_manifest_state -ne "MISSING_EXPECTED_P0_PREIMAGE" -and
  [string]$preflight.government_manifest_state -ne "PRESENT_VERIFIED_IDEMPOTENT"
) {
  throw ("GOVERNMENT_MANIFEST_PREIMAGE_UNRECOGNIZED={0}" -f [string]$preflight.government_manifest_state)
}

"===== MEGA BATCH 01 TO 06 UNIFIED PLANNING WHATIF ====="
"PREFLIGHT_MANIFEST_BINDING=PASS"
("PREFLIGHT_PACKAGE_ID={0}" -f $expectedPackageId)
("GOVERNMENT_MANIFEST_STATE={0}" -f [string]$preflight.government_manifest_state)
("GOVERNMENT_SQLITE_STATE={0}" -f [string]$preflight.government_sqlite_state)
"WHATIF_STATUS=COMPLETE"
"WHATIF_SCOPE=PLANNING_AND_CHANGE_DOMAIN_ONLY"
"MB1_PREDICTED_MUTATION=workspaces/palwakf_government/workspace_manifest.json_only"
"MB1_GOVERNMENT_SQLITE_MUTATION=NONE"
"MB2_PREDICTED_MUTATION=EVIDENCE_ONLY"
"MB3_PREDICTED_MUTATION=EVIDENCE_LEDGER_AND_HUMAN_REVIEW_FOUNDATION"
"MB4_PREDICTED_MUTATION=SCOPED_ISOLATED_WORKSPACE_CAPABILITY_FOUNDATIONS"
"MB5_PREDICTED_MUTATION=DETERMINISTIC_READ_PREPARE_TOOLS_ONLY"
"MB6_PILOT_EXECUTION=GATED_REQUIRES_EXPLICIT_PILOT_PAYLOAD"
"PILOT_PAYLOAD_REQUIRED=pilot_workspace_id,pilot_prompt,human_reviewer"
"MODEL_EXECUTION=NONE"
"SHELL_EXECUTION=NONE"
"GIT_WRITE=NONE"
"DEPLOYMENT=NONE"
"EXTERNAL_NETWORK=NONE"
"PROJECT_MUTATION=NONE_DURING_WHATIF"
