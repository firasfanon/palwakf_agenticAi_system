[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$modulePath = Join-Path $Root 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'

if (-not (Test-Path -LiteralPath $modulePath)) { throw "RUNTIME_MODULE_NOT_FOUND=$modulePath" }
Import-Module $modulePath -Force

$validBody = @'
ROLE=coordinator
TASK_STATUS=ANALYSIS_COMPLETE
TASK_CLASS=READ_ONLY_EVIDENCE_ANALYSIS
TRUTH_SOURCE=APPROVED_REFERENCE_CONTENT_ONLY
LIVE_STATE_PROVEN=NO
MUTATION_ALLOWED=NO
EVIDENCE_STATUS=EVIDENCE_MANIFEST_USED
EVIDENCE_REFERENCE_IDS=EVD-001
UNCERTAINTY_STATUS=LIMITED_TO_REFERENCE_EVIDENCE
SECURITY_POSTURE=UNTRUSTED_REFERENCE_CONTENT_NOT_EXECUTED
NEXT_STEP=HUMAN_REVIEW_REQUIRED
'@

$trailingBody = @(
  $validBody.TrimEnd([char[]]"`r`n")
  'REFERENCE_EVIDENCE:'
  'Reference path: reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md'
) -join "`n"

$leadingBody = @(
  'Explanation:'
  $validBody.TrimEnd([char[]]"`r`n")
) -join "`n"

$wrongRoleBody = $validBody.Replace('ROLE=coordinator', 'ROLE=sovereignty_reviewer')
$boundaryBody = @(
  'OUTPUT_CONTRACT_START'
  $validBody.TrimEnd([char[]]"`r`n")
) -join "`n"

$cases = @(
  [PSCustomObject]@{
    case_id = 'MODEL_BODY_VALID_AND_CANONICAL_ENVELOPE_CREATED'
    raw = $validBody
    expected_valid = $true
    expected_reason = 'MODEL_OUTPUT_VALID'
    canonical_required = $true
  },
  [PSCustomObject]@{
    case_id = 'TRAILING_REFERENCE_TEXT_REJECTED'
    raw = $trailingBody
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BODY_LINE_COUNT_INVALID'
    canonical_required = $false
  },
  [PSCustomObject]@{
    case_id = 'LEADING_TEXT_REJECTED'
    raw = $leadingBody
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BODY_LINE_COUNT_INVALID'
    canonical_required = $false
  },
  [PSCustomObject]@{
    case_id = 'WRONG_ROLE_REJECTED'
    raw = $wrongRoleBody
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_ROLE_VALUE_INVALID'
    canonical_required = $false
  },
  [PSCustomObject]@{
    case_id = 'MODEL_BOUNDARY_MARKER_REJECTED'
    raw = $boundaryBody
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BODY_LINE_COUNT_INVALID'
    canonical_required = $false
  }
)

$results = @()
foreach ($case in $cases) {
  $actual = Test-ReadOnlyModelOutputV1 `
    -RawOutput $case.raw `
    -ProjectRoot $Root `
    -ExpectedRole 'coordinator' `
    -ExpectedEvidenceIds @('EVD-001')

  $canonicalPass = if ($case.canonical_required) {
    $actual.canonical_output.StartsWith('OUTPUT_CONTRACT_START') -and
    $actual.canonical_output.EndsWith('OUTPUT_CONTRACT_END')
  } else {
    [string]::IsNullOrWhiteSpace($actual.canonical_output)
  }

  $passed = (
    $actual.valid -eq $case.expected_valid -and
    $actual.reason -eq $case.expected_reason -and
    $canonicalPass
  )

  $results += [PSCustomObject]@{
    case_id = $case.case_id
    passed = $passed
    actual_valid = $actual.valid
    actual_reason = $actual.reason
    raw_line_count = $actual.raw_line_count
    trailing_line_count = $actual.trailing_line_count
    trailing_text_sha256 = $actual.trailing_text_sha256
    canonical_envelope_valid = $canonicalPass
  }
}

$outputDir = Join-Path $Root 'output\evals'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$reportPath = Join-Path $outputDir "SYSTEM_OWNED_OUTPUT_ENVELOPE_EVAL_REPORT_$stamp.json"
$results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8

$passCount = @($results | Where-Object { $_.passed }).Count
$failCount = $results.Count - $passCount

"EVAL_CASE_COUNT=$($results.Count)"
"EVAL_PASSED_COUNT=$passCount"
"EVAL_FAILED_COUNT=$failCount"
"EVAL_REPORT_PATH=$reportPath"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if ($failCount -eq 0) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
