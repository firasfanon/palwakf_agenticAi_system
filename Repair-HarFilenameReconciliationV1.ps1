# UTF-8 with BOM. Compatible with Windows PowerShell 5.1 and PowerShell 7+.
[CmdletBinding()]
param(
  [string]$ProjectRoot = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $invokedScriptPath = $PSCommandPath
  if ([string]::IsNullOrWhiteSpace($invokedScriptPath)) { $invokedScriptPath = $MyInvocation.MyCommand.Path }
  if ([string]::IsNullOrWhiteSpace($invokedScriptPath)) { throw 'PROJECT_ROOT_REQUIRED__PASS_PROJECTROOT_EXPLICITLY.' }
  $invokedScriptDirectory = Split-Path -Parent $invokedScriptPath
  $ProjectRoot = Split-Path -Parent $invokedScriptDirectory
}

$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$RepairScriptPath = $PSCommandPath
if ([string]::IsNullOrWhiteSpace($RepairScriptPath)) { $RepairScriptPath = $MyInvocation.MyCommand.Path }
if ([string]::IsNullOrWhiteSpace($RepairScriptPath)) { throw 'REPAIR_SCRIPT_PATH_UNRESOLVED.' }
$RepairScriptDirectory = Split-Path -Parent $RepairScriptPath
$PayloadRoot = Join-Path -Path $RepairScriptDirectory -ChildPath 'PATCH_PAYLOAD'
$TargetRunner = Join-Path -Path $Root -ChildPath 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$TargetGate = Join-Path -Path $Root -ChildPath 'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
$PayloadRunner = Join-Path -Path $PayloadRoot -ChildPath 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$PayloadGate = Join-Path -Path $PayloadRoot -ChildPath 'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
$ExpectedRunnerSha256 = 'E0485D2FBA09DC2CEB6F269C59220C030FABBE451BA760BE81F4631955D966E5'
$ExpectedGateSha256 = '8384DC6E9C1CE0289B3AC46BDFE99F01494159EF0636DB054C151C13AE4874E1'
$BackupRoot = $null

function Get-ParserErrorsSafe {
  param([Parameter(Mandatory = $true)][string]$Path)
  $tokens = $null
  $parseErrors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$parseErrors)
  return @($parseErrors)
}

try {
  foreach ($requiredPath in @($TargetRunner, $TargetGate, $PayloadRunner, $PayloadGate)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) { throw "REQUIRED_FILE_MISSING: $requiredPath" }
  }

  $actualRunnerSha256 = (Get-FileHash -LiteralPath $TargetRunner -Algorithm SHA256).Hash.ToUpperInvariant()
  $actualGateSha256 = (Get-FileHash -LiteralPath $TargetGate -Algorithm SHA256).Hash.ToUpperInvariant()
  if ($actualRunnerSha256 -ne $ExpectedRunnerSha256) {
    throw "RUNNER_PREIMAGE_HASH_MISMATCH: expected=$ExpectedRunnerSha256 actual=$actualRunnerSha256"
  }
  if ($actualGateSha256 -ne $ExpectedGateSha256) {
    throw "STATIC_GATE_PREIMAGE_HASH_MISMATCH: expected=$ExpectedGateSha256 actual=$actualGateSha256"
  }

  $runnerParseBefore = @(Get-ParserErrorsSafe -Path $TargetRunner)
  $gateParseBefore = @(Get-ParserErrorsSafe -Path $TargetGate)
  if ($runnerParseBefore.Count -ne 0 -or $gateParseBefore.Count -ne 0) {
    throw "PREIMAGE_PARSER_FAILURE: runner_errors=$($runnerParseBefore.Count) gate_errors=$($gateParseBefore.Count)"
  }

  $backupParent = Join-Path -Path $Root -ChildPath 'backups'
  $backupName = 'har_filename_reconciliation_v1_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
  $BackupRoot = Join-Path -Path $backupParent -ChildPath $backupName
  $backupScripts = Join-Path -Path $BackupRoot -ChildPath 'scripts'
  New-Item -ItemType Directory -Path $backupScripts -Force | Out-Null
  Copy-Item -LiteralPath $TargetRunner -Destination (Join-Path -Path $backupScripts -ChildPath 'Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1') -Force
  Copy-Item -LiteralPath $TargetGate -Destination (Join-Path -Path $backupScripts -ChildPath 'Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1') -Force

  Copy-Item -LiteralPath $PayloadRunner -Destination $TargetRunner -Force
  Copy-Item -LiteralPath $PayloadGate -Destination $TargetGate -Force

  $runnerParseAfter = @(Get-ParserErrorsSafe -Path $TargetRunner)
  $gateParseAfter = @(Get-ParserErrorsSafe -Path $TargetGate)
  if ($runnerParseAfter.Count -ne 0 -or $gateParseAfter.Count -ne 0) {
    throw "POSTIMAGE_PARSER_FAILURE: runner_errors=$($runnerParseAfter.Count) gate_errors=$($gateParseAfter.Count)"
  }

  $runnerText = Get-Content -LiteralPath $TargetRunner -Raw -Encoding UTF8
  $gateText = Get-Content -LiteralPath $TargetGate -Raw -Encoding UTF8
  if ($runnerText -notmatch 'function Resolve-HarEvidence') { throw 'POSTIMAGE_CONTRACT_MISSING: Resolve-HarEvidence' }
  if ($runnerText -notmatch 'HAR_FILENAME_AMBIGUOUS') { throw 'POSTIMAGE_CONTRACT_MISSING: HAR_FILENAME_AMBIGUOUS' }
  if ($runnerText -notmatch 'browser_network_har_resolution\.json') { throw 'POSTIMAGE_CONTRACT_MISSING: browser_network_har_resolution.json' }
  if ($gateText -notmatch 'runner_has_har_filename_reconciliation') { throw 'POSTIMAGE_STATIC_GATE_CONTRACT_MISSING: runner_has_har_filename_reconciliation' }
  if ($gateText -notmatch 'runner_rejects_ambiguous_har_evidence') { throw 'POSTIMAGE_STATIC_GATE_CONTRACT_MISSING: runner_rejects_ambiguous_har_evidence' }

  "PROJECT_ROOT=$Root"
  "BACKUP_ROOT=$BackupRoot"
  "RUNNER_PREIMAGE_SHA256=$actualRunnerSha256"
  "STATIC_GATE_PREIMAGE_SHA256=$actualGateSha256"
  "RUNNER_PARSER_ERROR_COUNT=0"
  "STATIC_GATE_PARSER_ERROR_COUNT=0"
  'HAR_FILENAME_RECONCILIATION_V1=PASS'
  exit 0
}
catch {
  $message = $_.Exception.Message
  if ($BackupRoot -and (Test-Path -LiteralPath $BackupRoot)) {
    $backupRunner = Join-Path -Path $BackupRoot -ChildPath 'scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
    $backupGate = Join-Path -Path $BackupRoot -ChildPath 'scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1'
    if (Test-Path -LiteralPath $backupRunner) { Copy-Item -LiteralPath $backupRunner -Destination $TargetRunner -Force }
    if (Test-Path -LiteralPath $backupGate) { Copy-Item -LiteralPath $backupGate -Destination $TargetGate -Force }
    'ROLLBACK=APPLIED'
  }
  "HAR_FILENAME_RECONCILIATION_V1=FAILED"
  "EXCEPTION_MESSAGE=$message"
  exit 1
}
