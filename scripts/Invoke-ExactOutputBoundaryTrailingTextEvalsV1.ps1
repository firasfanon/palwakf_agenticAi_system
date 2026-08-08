[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$modulePath = Join-Path $Root 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'

if (-not (Test-Path -LiteralPath $modulePath)) {
  throw "RUNTIME_MODULE_NOT_FOUND=$modulePath"
}

Import-Module $modulePath -Force

$validOutput = @'
OUTPUT_CONTRACT_START
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
OUTPUT_CONTRACT_END
'@

$trailingOutput = @(
  $validOutput.TrimEnd([char[]]"`r`n")
  'REFERENCE_EVIDENCE:'
  'Evidence identifier: EVD-001'
  'Snippet identifier: EVD-001-SNIP-01'
  'Reference path: reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md'
) -join "`n"

$leadingOutput = @(
  'Explanation:'
  $validOutput.TrimEnd([char[]]"`r`n")
) -join "`n"

$missingEndOutput = $validOutput.Replace("`nOUTPUT_CONTRACT_END", '')

$extraKeyOutput = $validOutput.Replace(
  'NEXT_STEP=HUMAN_REVIEW_REQUIRED',
  "NEXT_STEP=HUMAN_REVIEW_REQUIRED`nTASK_ID=PILOT_READ_ONLY_CONTEXT_EVIDENCE_001"
)

$badBoundaryOutput = $validOutput.Replace('OUTPUT_CONTRACT_START', 'MODEL_OUTPUT_START')

$cases = @(
  [PSCustomObject]@{
    case_id = 'EXACT_BOUNDARY_VALID'
    raw = $validOutput
    expected_valid = $true
    expected_reason = 'MODEL_OUTPUT_VALID'
  },
  [PSCustomObject]@{
    case_id = 'TRAILING_REFERENCE_TEXT_REJECTED'
    raw = $trailingOutput
    expected_valid = $false
    expected_reason = 'TRAILING_NONCONTRACT_TEXT_DETECTED'
  },
  [PSCustomObject]@{
    case_id = 'LEADING_TEXT_REJECTED'
    raw = $leadingOutput
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BOUNDARY_START_MISSING'
  },
  [PSCustomObject]@{
    case_id = 'MISSING_END_REJECTED'
    raw = $missingEndOutput
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BOUNDARY_END_MISSING'
  },
  [PSCustomObject]@{
    case_id = 'EXTRA_TASK_ID_REJECTED'
    raw = $extraKeyOutput
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BOUNDARY_LINE_COUNT_INVALID'
  },
  [PSCustomObject]@{
    case_id = 'BAD_BOUNDARY_REJECTED'
    raw = $badBoundaryOutput
    expected_valid = $false
    expected_reason = 'MODEL_OUTPUT_BOUNDARY_START_MISSING'
  }
)

$results = @()

foreach ($case in $cases) {
  $actual = Test-ReadOnlyModelOutputV1 `
    -RawOutput $case.raw `
    -ProjectRoot $Root `
    -ExpectedRole 'coordinator' `
    -ExpectedEvidenceIds @('EVD-001')

  $passed = (
    $actual.valid -eq $case.expected_valid -and
    $actual.reason -eq $case.expected_reason
  )

  $results += [PSCustomObject]@{
    case_id = $case.case_id
    passed = $passed
    actual_valid = $actual.valid
    actual_reason = $actual.reason
    trailing_line_count = $actual.trailing_line_count
    trailing_text_sha256 = $actual.trailing_text_sha256
  }
}

$outputDirectory = Join-Path $Root 'output\evals'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$reportPath = Join-Path $outputDirectory "EXACT_OUTPUT_BOUNDARY_TRAILING_TEXT_EVAL_REPORT_$stamp.json"

$results |
  ConvertTo-Json -Depth 6 |
  Set-Content -LiteralPath $reportPath -Encoding UTF8

$passedCount = @($results | Where-Object { $_.passed }).Count
$failedCount = $results.Count - $passedCount

"EVAL_CASE_COUNT=$($results.Count)"
"EVAL_PASSED_COUNT=$passedCount"
"EVAL_FAILED_COUNT=$failedCount"
"EVAL_REPORT_PATH=$reportPath"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if ($failedCount -eq 0) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
