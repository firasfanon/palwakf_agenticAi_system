# UTF-8 with BOM. Windows PowerShell 5.1 compatible.
[CmdletBinding()]
param(
  [string]$ProjectRoot = ''
)

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
$targetRunner = Join-Path $root 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'

if (-not (Test-Path -LiteralPath $payloadRunner)) { throw "PATCH_PAYLOAD_MISSING: $payloadRunner" }
if (-not (Test-Path -LiteralPath $targetRunner)) { throw "TARGET_RUNNER_MISSING: $targetRunner" }

function Get-ParserErrors {
  param([Parameter(Mandatory = $true)][string]$Path)
  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) | Out-Null
  return @($errors)
}

$payloadErrors = @(Get-ParserErrors -Path $payloadRunner)
if ($payloadErrors.Length -ne 0) {
  $details = ($payloadErrors | ForEach-Object { $_.Message }) -join ' | '
  throw "PAYLOAD_RUNNER_PARSER_FAILED: $details"
}

$backupRoot = Join-Path $root ("backups\windows_uat_runner_runtime_diagnostics_repair_v4_{0}" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
Copy-Item -LiteralPath $targetRunner -Destination (Join-Path $backupRoot 'Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1') -Force
Copy-Item -LiteralPath $payloadRunner -Destination $targetRunner -Force

$targetErrors = @(Get-ParserErrors -Path $targetRunner)
if ($targetErrors.Length -ne 0) {
  Copy-Item -LiteralPath (Join-Path $backupRoot 'Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1') -Destination $targetRunner -Force
  $details = ($targetErrors | ForEach-Object { $_.Message }) -join ' | '
  throw "TARGET_RUNNER_PARSER_FAILED_AFTER_COPY__ROLLBACK_APPLIED: $details"
}

$payloadHash = (Get-FileHash -LiteralPath $payloadRunner -Algorithm SHA256).Hash
$targetHash = (Get-FileHash -LiteralPath $targetRunner -Algorithm SHA256).Hash
if ($payloadHash -ne $targetHash) {
  Copy-Item -LiteralPath (Join-Path $backupRoot 'Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1') -Destination $targetRunner -Force
  throw 'TARGET_RUNNER_HASH_MISMATCH_AFTER_COPY__ROLLBACK_APPLIED.'
}

Write-Host "PROJECT_ROOT=$root"
Write-Host "BACKUP_ROOT=$backupRoot"
Write-Host "RUNNER_PARSER_ERROR_COUNT=0"
Write-Host "RUNNER_RUNTIME_DIAGNOSTICS_REPAIR_V4=PASS"
