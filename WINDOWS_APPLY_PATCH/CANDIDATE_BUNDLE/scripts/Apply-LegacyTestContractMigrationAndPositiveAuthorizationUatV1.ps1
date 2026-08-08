[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$BundleRoot = Split-Path -Parent $PSScriptRoot
$PayloadRoot = Join-Path $BundleRoot 'PATCH_PAYLOAD'
$PreimagePath = Join-Path $BundleRoot 'PREIMAGE_SHA256.json'

function Get-UpperSha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot" }
if (-not (Test-Path -LiteralPath $PayloadRoot -PathType Container)) { throw "PATCH_PAYLOAD_NOT_FOUND: $PayloadRoot" }
if (-not (Test-Path -LiteralPath $PreimagePath -PathType Leaf)) { throw "PREIMAGE_MANIFEST_NOT_FOUND: $PreimagePath" }

$preimage = Get-Content -LiteralPath $PreimagePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in $preimage.existing_files.PSObject.Properties) {
  $target = Join-Path $ProjectRoot $property.Name
  if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "PREIMAGE_TARGET_MISSING: $($property.Name)" }
  $actual = Get-UpperSha256 $target
  if ($actual -ne $property.Value) { throw "PREIMAGE_HASH_MISMATCH: $($property.Name) EXPECTED=$($property.Value) ACTUAL=$actual" }
}
foreach ($relative in @($preimage.must_be_absent)) {
  $target = Join-Path $ProjectRoot $relative
  if (Test-Path -LiteralPath $target) { throw "PREIMAGE_EXPECTED_ABSENT_BUT_EXISTS: $relative" }
}

$backupRoot = Join-Path $ProjectRoot ('backups\legacy_test_contract_migration_positive_authorization_uat_v1_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$rollback = [ordered]@{ project_root = $ProjectRoot; backup_root = $backupRoot; restored_files = @(); new_files = @() }

$payloadFiles = Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File
foreach ($payload in $payloadFiles) {
  $relative = $payload.FullName.Substring($PayloadRoot.FullName.Length).TrimStart('\','/')
  $target = Join-Path $ProjectRoot $relative
  if (Test-Path -LiteralPath $target -PathType Leaf) {
    $backup = Join-Path $backupRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
    Copy-Item -LiteralPath $target -Destination $backup -Force
    $rollback.restored_files += $relative
  }
  else { $rollback.new_files += $relative }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
  Copy-Item -LiteralPath $payload.FullName -Destination $target -Force
}
$rollback | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backupRoot 'rollback_manifest.json') -Encoding UTF8

$postimagePath = Join-Path $BundleRoot 'POSTIMAGE_SHA256.json'
$postimage = Get-Content -LiteralPath $postimagePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in $postimage.patch_files.PSObject.Properties) {
  $target = Join-Path $ProjectRoot $property.Name
  $actual = Get-UpperSha256 $target
  if ($actual -ne $property.Value) { throw "POSTIMAGE_HASH_MISMATCH: $($property.Name) EXPECTED=$($property.Value) ACTUAL=$actual" }
}

Write-Output "PROJECT_ROOT=$ProjectRoot"
Write-Output "BACKUP_ROOT=$backupRoot"
Write-Output 'PREIMAGE_VERIFICATION=PASS'
Write-Output 'POSTIMAGE_VERIFICATION=PASS'
Write-Output 'LEGACY_TEST_CONTRACT_MIGRATION_AND_CONTROLLED_POSITIVE_AUTHORIZATION_UAT_V1_APPLY=PASS'
