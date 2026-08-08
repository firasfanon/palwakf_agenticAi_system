[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$modulePath = Join-Path $Root 'runtime\StructuredAnalysisPayloadV1.psm1'
$caseRoot = Join-Path $Root 'evals\structured_analysis_payload_foundation\cases'

foreach ($requiredPath in @($modulePath, $caseRoot)) {
  if (-not (Test-Path -LiteralPath $requiredPath)) {
    throw "REQUIRED_PATH_NOT_FOUND=$requiredPath"
  }
}

Import-Module $modulePath -Force

$cases = @(
  @{ case_id = 'SAPF_VALID_KNOWLEDGE'; file = 'VALID_KNOWLEDGE_V1.json'; agent_id = 'knowledge_researcher'; expected_valid = $true },
  @{ case_id = 'SAPF_VALID_DOCUMENTATION'; file = 'VALID_DOCUMENTATION_V1.json'; agent_id = 'documentation_handoff'; expected_valid = $true },
  @{ case_id = 'SAPF_REJECT_EXTRA_FIELD'; file = 'INVALID_EXTRA_FIELD_V1.json'; agent_id = 'knowledge_researcher'; expected_valid = $false },
  @{ case_id = 'SAPF_REJECT_UNEXPECTED_EVIDENCE'; file = 'INVALID_UNEXPECTED_EVIDENCE_V1.json'; agent_id = 'knowledge_researcher'; expected_valid = $false },
  @{ case_id = 'SAPF_REJECT_HANDOFF_MISSING_REFERENCE'; file = 'INVALID_HANDOFF_MISSING_REFERENCE_V1.json'; agent_id = 'documentation_handoff'; expected_valid = $false },
  @{ case_id = 'SAPF_REJECT_KNOWLEDGE_MISSING_ASSESSMENT'; file = 'INVALID_KNOWLEDGE_MISSING_ASSESSMENT_V1.json'; agent_id = 'knowledge_researcher'; expected_valid = $false }
)

$results = @()

foreach ($case in $cases) {
  $raw = Get-Content -LiteralPath (Join-Path $caseRoot $case.file) -Raw -Encoding UTF8

  $validation = Test-StructuredAnalysisPayloadV1 `
    -RawOutput $raw `
    -ProjectRoot $Root `
    -AgentId $case.agent_id `
    -ExpectedEvidenceIds @('EVD-001', 'EVD-002') `
    -RunId 'SAPF-EVAL-RUN' `
    -TaskId 'SAPF-EVAL-TASK' `
    -EvidenceManifestId 'SAPF-EVAL-MANIFEST'

  $passed = ($validation.valid -eq $case.expected_valid)

  if ($case.expected_valid -eq $true) {
    $passed = $passed -and ($validation.canonical_output -like '*STRUCTURED_ANALYSIS_PAYLOAD_START*') -and ($validation.canonical_output -like '*STRUCTURED_ANALYSIS_PAYLOAD_END*')
  }

  $results += [pscustomobject]@{
    case_id = $case.case_id
    expected_valid = $case.expected_valid
    actual_valid = $validation.valid
    validation_reason = $validation.reason
    passed = $passed
  }
}

$outputDirectory = Join-Path $Root 'output\evals'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$reportPath = Join-Path $outputDirectory "STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_EVAL_REPORT_$stamp.json"

$results | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8

$passedCount = @($results | Where-Object { $_.passed }).Count
$failedCount = $results.Count - $passedCount

"EVAL_CASE_COUNT=$($results.Count)"
"EVAL_PASSED_COUNT=$passedCount"
"EVAL_FAILED_COUNT=$failedCount"
"EVAL_REPORT_PATH=$reportPath"
'TASK_GENERATION=NONE'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'

if ($failedCount -eq 0) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
