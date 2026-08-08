# UTF-8 with BOM. Windows PowerShell 5.1 compatible.
[CmdletBinding()]
param(
  [string]$ProjectRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $scriptPathForRoot = $PSCommandPath
  if ([string]::IsNullOrWhiteSpace($scriptPathForRoot)) { $scriptPathForRoot = $MyInvocation.MyCommand.Path }
  if ([string]::IsNullOrWhiteSpace($scriptPathForRoot)) { throw 'PROJECT_ROOT_REQUIRED__PASS_PROJECTROOT_OR_RUN_WITH_POWERSHELL_FILE_MODE.' }
  $scriptDirectoryForRoot = Split-Path -Parent $scriptPathForRoot
  $ProjectRoot = Split-Path -Parent $scriptDirectoryForRoot
}

$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$payloadRoot = Join-Path $PSScriptRoot 'PATCH_PAYLOAD'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupRoot = Join-Path $Root ("backups\windows_uat_runner_worktree_cleanup_repair_v8_{0}" -f $timestamp)
$targets = @(
  'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1',
  'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
)

if (-not (Test-Path -LiteralPath $payloadRoot)) { throw "PATCH_PAYLOAD_MISSING: $payloadRoot" }
foreach ($relative in $targets) {
  $target = Join-Path $Root $relative
  $source = Join-Path $payloadRoot $relative
  if (-not (Test-Path -LiteralPath $target)) { throw "TARGET_MISSING: $target" }
  if (-not (Test-Path -LiteralPath $source)) { throw "PAYLOAD_MISSING: $source" }
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
foreach ($relative in $targets) {
  $target = Join-Path $Root $relative
  $backup = Join-Path $backupRoot $relative
  New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
  Copy-Item -LiteralPath $target -Destination $backup -Force
  Copy-Item -LiteralPath (Join-Path $payloadRoot $relative) -Destination $target -Force
}

$parseTargets = @(
  Join-Path $Root 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1',
  Join-Path $Root 'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
)
$totalErrors = 0
foreach ($file in $parseTargets) {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($file, [ref]$tokens, [ref]$errors)
  $errorCount = @($errors).Count
  "PARSER_ERROR_COUNT[$([System.IO.Path]::GetFileName($file))]=$errorCount"
  $totalErrors += $errorCount
}
if ($totalErrors -ne 0) {
  foreach ($relative in $targets) {
    Copy-Item -LiteralPath (Join-Path $backupRoot $relative) -Destination (Join-Path $Root $relative) -Force
  }
  throw 'RUNNER_WORKTREE_CLEANUP_REPAIR_V8_ROLLED_BACK_DUE_TO_PARSER_ERRORS.'
}

"PROJECT_ROOT=$Root"
"BACKUP_ROOT=$backupRoot"
'RUNNER_WORKTREE_CLEANUP_REPAIR_V8=PASS'
