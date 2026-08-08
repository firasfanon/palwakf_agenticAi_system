[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$runnerPath = Join-Path $Root 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'

if (-not (Test-Path -LiteralPath $runnerPath)) {
  throw "RUNNER_NOT_FOUND=$runnerPath"
}

$runner = Get-Content -LiteralPath $runnerPath -Raw -Encoding UTF8

$securityFilterRequired = '$flags = @($_.security_flags | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })'
$codeFenceVariableRequired = '$codeFence = ''```'''
$codeFenceOutputRequired = '${codeFence}text'

$checks = [ordered]@{
  SECURITY_EMPTY_FLAGS_FILTER_PRESENT = $runner.Contains($securityFilterRequired)
  EMPTY_SECURITY_SIGNAL_PRESENT = $runner.Contains('NO_DETECTED_SECURITY_FLAG')
  CODE_FENCE_VARIABLE_PRESENT = $runner.Contains($codeFenceVariableRequired)
  CODE_FENCE_OUTPUT_PRESENT = $runner.Contains($codeFenceOutputRequired)
  RAW_MARKDOWN_TEXT_FENCE_PRESENT = $runner.Contains('```text')
  RAW_PROVIDER_OUTPUT_SECTION_PRESENT = $runner.Contains('## Raw provider model output')
  CANONICAL_ENVELOPE_REPORT_SECTION_PRESENT = $runner.Contains('## Canonical system-owned envelope')
  CANONICAL_OUTPUT_PATH_PRESENT = $runner.Contains('CANONICAL_OUTPUT_PATH=')
  SYSTEM_OWNED_ENVELOPE_RESULT_PRESENT = $runner.Contains('SYSTEM_OWNED_ENVELOPE_CREATED=')
}

$emptyFlags = @(@($null) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
$checks['SECURITY_EMPTY_FLAGS_RUNTIME_PASS'] = ($emptyFlags.Count -eq 0)

"RUNNER_EXISTS=True"
foreach ($name in $checks.Keys) {
  "$name=$($checks[$name])"
}
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

$pass = (
  $checks['SECURITY_EMPTY_FLAGS_FILTER_PRESENT'] -and
  $checks['EMPTY_SECURITY_SIGNAL_PRESENT'] -and
  $checks['CODE_FENCE_VARIABLE_PRESENT'] -and
  $checks['CODE_FENCE_OUTPUT_PRESENT'] -and
  (-not $checks['RAW_MARKDOWN_TEXT_FENCE_PRESENT']) -and
  $checks['RAW_PROVIDER_OUTPUT_SECTION_PRESENT'] -and
  $checks['CANONICAL_ENVELOPE_REPORT_SECTION_PRESENT'] -and
  $checks['CANONICAL_OUTPUT_PATH_PRESENT'] -and
  $checks['SYSTEM_OWNED_ENVELOPE_RESULT_PRESENT'] -and
  $checks['SECURITY_EMPTY_FLAGS_RUNTIME_PASS']
)

if ($pass) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
