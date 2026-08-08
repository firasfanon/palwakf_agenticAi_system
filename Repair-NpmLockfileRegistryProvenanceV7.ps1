# UTF-8 with BOM. Windows PowerShell 5.1 compatible.
[CmdletBinding()]
param(
  [string]$ProjectRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $scriptPath = $PSCommandPath
  if ([string]::IsNullOrWhiteSpace($scriptPath)) { $scriptPath = $MyInvocation.MyCommand.Path }
  if ([string]::IsNullOrWhiteSpace($scriptPath)) { throw 'PROJECT_ROOT_REQUIRED__PASS_PROJECTROOT.' }
  $ProjectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
}

$root = [System.IO.Path]::GetFullPath($ProjectRoot)
$payloadRoot = Join-Path $PSScriptRoot 'PATCH_PAYLOAD'
$payloadRunner = Join-Path $payloadRoot 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$payloadGate = Join-Path $payloadRoot 'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
$targetRunner = Join-Path $root 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$targetGate = Join-Path $root 'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
$targetLock = Join-Path $root 'frontend\package-lock.json'

foreach ($path in @($payloadRunner, $payloadGate, $targetRunner, $targetGate, $targetLock)) {
  if (-not (Test-Path -LiteralPath $path)) { throw "REQUIRED_PATH_MISSING: $path" }
}

function Get-ParserErrors {
  param([Parameter(Mandatory = $true)][string]$Path)
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
  return @($errors)
}

$payloadRunnerErrors = @(Get-ParserErrors -Path $payloadRunner)
$payloadGateErrors = @(Get-ParserErrors -Path $payloadGate)
if ($payloadRunnerErrors.Length -ne 0 -or $payloadGateErrors.Length -ne 0) {
  $details = @($payloadRunnerErrors + $payloadGateErrors | ForEach-Object { $_.Message }) -join ' | '
  throw "PATCH_PAYLOAD_PARSER_FAILED: $details"
}

$internalPrefix = 'https://packages.applied-caas-gateway1.internal.api.openai.org/artifactory/api/npm/npm-public/'
$publicPrefix = 'https://registry.npmjs.org/'
$originalLockText = [System.IO.File]::ReadAllText($targetLock, [System.Text.Encoding]::UTF8)
$internalCount = [regex]::Matches($originalLockText, [regex]::Escape($internalPrefix)).Count
if ($internalCount -le 0) {
  throw 'LOCKFILE_PREIMAGE_NOT_EXPECTED: no internal build-registry resolved URLs were found. No mutation applied.'
}
$expectedLockText = $originalLockText.Replace($internalPrefix, $publicPrefix)
if ($expectedLockText -eq $originalLockText) { throw 'LOCKFILE_REWRITE_NOOP.' }

$backupRoot = Join-Path $root ("backups\npm_lockfile_registry_provenance_repair_v7_{0}" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backupRunner = Join-Path $backupRoot 'Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$backupGate = Join-Path $backupRoot 'Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
$backupLock = Join-Path $backupRoot 'package-lock.json'
Copy-Item -LiteralPath $targetRunner -Destination $backupRunner -Force
Copy-Item -LiteralPath $targetGate -Destination $backupGate -Force
Copy-Item -LiteralPath $targetLock -Destination $backupLock -Force

try {
  Copy-Item -LiteralPath $payloadRunner -Destination $targetRunner -Force
  Copy-Item -LiteralPath $payloadGate -Destination $targetGate -Force
  [System.IO.File]::WriteAllText($targetLock, $expectedLockText, (New-Object System.Text.UTF8Encoding($false)))

  $targetRunnerErrors = @(Get-ParserErrors -Path $targetRunner)
  $targetGateErrors = @(Get-ParserErrors -Path $targetGate)
  if ($targetRunnerErrors.Length -ne 0 -or $targetGateErrors.Length -ne 0) {
    $details = @($targetRunnerErrors + $targetGateErrors | ForEach-Object { $_.Message }) -join ' | '
    throw "TARGET_PARSER_FAILED_AFTER_COPY: $details"
  }

  $postLockText = [System.IO.File]::ReadAllText($targetLock, [System.Text.Encoding]::UTF8)
  if ($postLockText -cne $expectedLockText) { throw 'LOCKFILE_POSTIMAGE_TEXT_MISMATCH.' }
  $postInternalCount = [regex]::Matches($postLockText, [regex]::Escape($internalPrefix)).Count
  $postPublicCount = [regex]::Matches($postLockText, [regex]::Escape($publicPrefix)).Count
  if ($postInternalCount -ne 0) { throw "LOCKFILE_INTERNAL_REGISTRY_RESIDUAL_COUNT=$postInternalCount" }
  if ($postPublicCount -lt $internalCount) { throw "LOCKFILE_PUBLIC_REGISTRY_REWRITE_COUNT_TOO_LOW: expected_at_least=$internalCount actual=$postPublicCount" }

  foreach ($pair in @(
    [pscustomobject]@{ payload = $payloadRunner; target = $targetRunner },
    [pscustomobject]@{ payload = $payloadGate; target = $targetGate }
  )) {
    $payloadHash = (Get-FileHash -LiteralPath $pair.payload -Algorithm SHA256).Hash
    $targetHash = (Get-FileHash -LiteralPath $pair.target -Algorithm SHA256).Hash
    if ($payloadHash -ne $targetHash) { throw "TARGET_HASH_MISMATCH_AFTER_COPY: $($pair.target)" }
  }
}
catch {
  Copy-Item -LiteralPath $backupRunner -Destination $targetRunner -Force
  Copy-Item -LiteralPath $backupGate -Destination $targetGate -Force
  Copy-Item -LiteralPath $backupLock -Destination $targetLock -Force
  throw "NPM_LOCKFILE_REGISTRY_PROVENANCE_REPAIR_V7_FAILED__ROLLBACK_APPLIED: $($_.Exception.Message)"
}

Write-Host "PROJECT_ROOT=$root"
Write-Host "BACKUP_ROOT=$backupRoot"
Write-Host "LOCKFILE_INTERNAL_REGISTRY_PREIMAGE_COUNT=$internalCount"
Write-Host "LOCKFILE_INTERNAL_REGISTRY_POSTIMAGE_COUNT=0"
Write-Host "LOCKFILE_PUBLIC_REGISTRY_RESOLVED_COUNT=$postPublicCount"
Write-Host 'RUNNER_PARSER_ERROR_COUNT=0'
Write-Host 'STATIC_GATE_PARSER_ERROR_COUNT=0'
Write-Host 'NPM_LOCKFILE_REGISTRY_PROVENANCE_REPAIR_V7=PASS'
