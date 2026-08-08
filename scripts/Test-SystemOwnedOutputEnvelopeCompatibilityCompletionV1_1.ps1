[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$checks = @(
  @{
    name = 'BASELINE_EVALS_V3'
    path = 'scripts\Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1'
    markers = @(
      'MODEL_OUTPUT_CONTRACT_V3_SYSTEM_OWNED_ENVELOPE',
      'EVAL_VALID_MODEL_BODY_CANONICAL_ENVELOPE_CREATED_V3',
      'EVAL_MODEL_BOUNDARY_MARKER_REJECTED_V3'
    )
  },
  @{
    name = 'REPORT_TEST_CANONICAL_AWARE'
    path = 'scripts\Test-DryRunReportRenderingIntegrityClosureV1.ps1'
    markers = @(
      'CANONICAL_ENVELOPE_REPORT_SECTION_PRESENT',
      'CANONICAL_OUTPUT_PATH_PRESENT',
      'SYSTEM_OWNED_ENVELOPE_RESULT_PRESENT'
    )
  },
  @{
    name = 'SYSTEM_ENVELOPE_EVALS'
    path = 'scripts\Invoke-SystemOwnedOutputEnvelopeEvalsV1.ps1'
    markers = @(
      'TRAILING_REFERENCE_TEXT_REJECTED',
      'MODEL_BOUNDARY_MARKER_REJECTED'
    )
  }
)

$failures = @()

foreach ($check in $checks) {
  $path = Join-Path $Root $check.path

  if (-not (Test-Path -LiteralPath $path)) {
    $failures += "$($check.name):MISSING_FILE"
    continue
  }

  $text = Get-Content -LiteralPath $path -Raw -Encoding UTF8

  foreach ($marker in $check.markers) {
    if (-not $text.Contains($marker)) {
      $failures += "$($check.name):MISSING_MARKER:$marker"
    }
  }
}

"COMPATIBILITY_CHECK_COUNT=$($checks.Count)"
"COMPATIBILITY_FAILURE_COUNT=$($failures.Count)"
"COMPATIBILITY_FAILURES=$([string]::Join(';', $failures))"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if ($failures.Count -eq 0) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
