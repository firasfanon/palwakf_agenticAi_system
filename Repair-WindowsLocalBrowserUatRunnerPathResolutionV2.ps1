# UTF-8 with BOM. Compatible with Windows PowerShell 5.1 and PowerShell 7+.
[CmdletBinding()]
param(
  [string]$ProjectRoot = '',
  [string]$PayloadRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptPath = $PSCommandPath
if ([string]::IsNullOrWhiteSpace($scriptPath)) { $scriptPath = $MyInvocation.MyCommand.Path }
if ([string]::IsNullOrWhiteSpace($scriptPath)) { throw 'SCRIPT_PATH_UNAVAILABLE__RUN_WITH_POWERSHELL_FILE_MODE.' }
$scriptDirectory = Split-Path -Parent $scriptPath

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = (Get-Location).Path }
if ([string]::IsNullOrWhiteSpace($PayloadRoot)) { $PayloadRoot = Join-Path $scriptDirectory 'PATCH_PAYLOAD' }

$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$Payload = [System.IO.Path]::GetFullPath($PayloadRoot)
$runnerName = 'Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$staticName = 'Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
$targetScripts = Join-Path $Root 'scripts'
$sourceScripts = Join-Path $Payload 'scripts'
$targetRunner = Join-Path $targetScripts $runnerName
$targetStatic = Join-Path $targetScripts $staticName
$sourceRunner = Join-Path $sourceScripts $runnerName
$sourceStatic = Join-Path $sourceScripts $staticName
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$backupRoot = Join-Path $Root ("backups\windows_uat_runner_path_resolution_repair_v2_$timestamp")
$reportRoot = Join-Path $Root 'output\windows_local_browser_uat_runner_repair'
$reportPath = Join-Path $reportRoot ("RUNNER_PATH_RESOLUTION_REPAIR_V2_$timestamp.json")

function Get-FileSha256 {
  param([Parameter(Mandatory = $true)][string]$Path)
  (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-ParserErrors {
  param([Parameter(Mandatory = $true)][string]$Path)
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
  @($errors)
}

foreach ($path in @($sourceRunner, $sourceStatic)) {
  if (-not (Test-Path -LiteralPath $path)) { throw "PATCH_PAYLOAD_FILE_MISSING: $path" }
}
if (-not (Test-Path -LiteralPath $targetScripts)) { throw "PROJECT_SCRIPTS_DIRECTORY_MISSING: $targetScripts" }

$payloadParser = [ordered]@{}
foreach ($path in @($sourceRunner, $sourceStatic)) {
  $errors = Get-ParserErrors -Path $path
  $payloadParser[(Split-Path -Leaf $path)] = $errors.Count
  if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error "PAYLOAD_PARSER_ERROR [$($_.Extent.StartLineNumber):$($_.Extent.StartColumnNumber)] $($_.Message)" }
    throw 'PATCH_PAYLOAD_PARSER_GATE_FAILED.'
  }
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$before = [ordered]@{}
foreach ($target in @($targetRunner, $targetStatic)) {
  if (Test-Path -LiteralPath $target) {
    $leaf = Split-Path -Leaf $target
    $before[$leaf] = Get-FileSha256 -Path $target
    Copy-Item -LiteralPath $target -Destination (Join-Path $backupRoot $leaf) -Force
  }
}

$restoreRequired = $true
try {
  Copy-Item -LiteralPath $sourceRunner -Destination $targetRunner -Force
  Copy-Item -LiteralPath $sourceStatic -Destination $targetStatic -Force

  $targetParser = [ordered]@{}
  foreach ($path in @($targetRunner, $targetStatic)) {
    $errors = Get-ParserErrors -Path $path
    $targetParser[(Split-Path -Leaf $path)] = $errors.Count
    if ($errors.Count -gt 0) {
      $errors | ForEach-Object { Write-Error "TARGET_PARSER_ERROR [$($_.Extent.StartLineNumber):$($_.Extent.StartColumnNumber)] $($_.Message)" }
      throw 'TARGET_PARSER_GATE_FAILED.'
    }
  }

  $after = [ordered]@{
    $runnerName = Get-FileSha256 -Path $targetRunner
    $staticName = Get-FileSha256 -Path $targetStatic
  }
  $report = [ordered]@{
    result = 'PASS'
    timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    project_root = $Root
    backup_root = $backupRoot
    changed_files = @($runnerName, $staticName)
    payload_parser_error_counts = $payloadParser
    target_parser_error_counts = $targetParser
    before_sha256 = $before
    after_sha256 = $after
    next_required_command = '.\scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
  }
  $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
  $restoreRequired = $false
  'RUNNER_PATH_RESOLUTION_REPAIR_V2=PASS'
  "BACKUP_ROOT=$backupRoot"
  "REPORT=$reportPath"
  "RUNNER_SHA256=$($after[$runnerName])"
  "STATIC_GATE_SHA256=$($after[$staticName])"
  'NEXT=Run static gate and require RUNNER_PARSER_ERROR_COUNT=0 and FINAL_RESULT=PASS.'
}
catch {
  if ($restoreRequired) {
    foreach ($name in @($runnerName, $staticName)) {
      $backup = Join-Path $backupRoot $name
      $target = Join-Path $targetScripts $name
      if (Test-Path -LiteralPath $backup) { Copy-Item -LiteralPath $backup -Destination $target -Force }
    }
  }
  throw
}
