[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$PackageRoot = $PSScriptRoot
$Payload = Join-Path $PackageRoot 'PATCH_PAYLOAD\scripts\Test-LegacyTestContractMigrationAndPositiveAuthorizationUatV1Static.ps1'
$Target = Join-Path $ProjectRoot 'scripts\Test-LegacyTestContractMigrationAndPositiveAuthorizationUatV1Static.ps1'
$ExpectedPreimage = '58197383AA0FF931A6DE141A6540B3CF528A4F58DBD0C859FCCD83491839CBEE'
$ExpectedPostimage = '9602E3FFF2A1FDD7F4CBEC441B3F7A33C07CE1C1512FDCEED92A5EEC3A989BF9'

function Get-UpperSha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot" }
if (-not (Test-Path -LiteralPath $Payload -PathType Leaf)) { throw "PATCH_PAYLOAD_NOT_FOUND: $Payload" }
if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) { throw "STATIC_GATE_TARGET_NOT_FOUND: $Target" }

$current = Get-UpperSha256 $Target
if (($current -ne $ExpectedPreimage) -and ($current -ne $ExpectedPostimage)) {
  throw "STATIC_GATE_PREIMAGE_UNRECOGNIZED: EXPECTED_PRE=$ExpectedPreimage EXPECTED_POST=$ExpectedPostimage ACTUAL=$current"
}

$backupRoot = Join-Path $ProjectRoot ('backups\legacy_test_contract_static_gate_reconciliation_v1_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
Copy-Item -LiteralPath $Target -Destination (Join-Path $backupRoot 'Test-LegacyTestContractMigrationAndPositiveAuthorizationUatV1Static.ps1') -Force

$applied = 'ALREADY_RECONCILED'
if ($current -eq $ExpectedPreimage) {
  Copy-Item -LiteralPath $Payload -Destination $Target -Force
  $applied = 'PATCHED'
}
$post = Get-UpperSha256 $Target
if ($post -ne $ExpectedPostimage) { throw "STATIC_GATE_POSTIMAGE_HASH_MISMATCH: EXPECTED=$ExpectedPostimage ACTUAL=$post" }

$parseTokens = $null
$parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile($Target, [ref]$parseTokens, [ref]$parseErrors) | Out-Null
$parseErrorCount = @($parseErrors).Count
if ($parseErrorCount -ne 0) {
  throw ('STATIC_GATE_PARSER_ERRORS: ' + ((@($parseErrors) | ForEach-Object { $_.Message }) -join ' | '))
}

Write-Output "PROJECT_ROOT=$ProjectRoot"
Write-Output "BACKUP_ROOT=$backupRoot"
Write-Output "STATIC_GATE_PREIMAGE_SHA256=$current"
Write-Output "STATIC_GATE_POSTIMAGE_SHA256=$post"
Write-Output "STATIC_GATE_APPLY_MODE=$applied"
Write-Output "STATIC_GATE_PARSER_ERROR_COUNT=$parseErrorCount"
Write-Output 'LEGACY_TEST_CONTRACT_STATIC_GATE_RECONCILIATION_V1=PASS'
