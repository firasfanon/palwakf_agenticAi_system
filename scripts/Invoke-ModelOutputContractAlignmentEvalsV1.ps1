[CmdletBinding()]
param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference='Stop'
$Root=[System.IO.Path]::GetFullPath($ProjectRoot)
Import-Module (Join-Path $Root 'runtime/ReadOnlyRuntimeContextEvidenceV1.psm1') -Force
$cases=@()
function Add-CaseResult { param([string]$Id,[bool]$Passed,[string]$Reason) $script:cases += [ordered]@{eval_id=$Id;passed=$Passed;reason=$Reason} }

$manifest=[pscustomobject]@{ evidence_items=@([pscustomobject]@{evidence_id='EVD-001'}) }

$valid=@"
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
"@

$validResult=Test-ReadOnlyModelOutput -Raw $valid -AgentId 'coordinator' -Manifest $manifest
Add-CaseResult 'EVAL_MODEL_OUTPUT_VALID_V1' $validResult.passed $validResult.reason

$extraTaskId=@"
TASK_ID=PILOT_READ_ONLY_CONTEXT_EVIDENCE_001
$valid
"@
$extraTaskIdResult=Test-ReadOnlyModelOutput -Raw $extraTaskId -AgentId 'coordinator' -Manifest $manifest
Add-CaseResult 'EVAL_MODEL_OUTPUT_FORBIDDEN_TASK_ID_V1' ((-not $extraTaskIdResult.passed) -and ($extraTaskIdResult.reason -eq 'MODEL_OUTPUT_FORBIDDEN_KEY=TASK_ID')) $extraTaskIdResult.reason

$unknown=@"
EXTRA_FIELD=NO
$valid
"@
$unknownResult=Test-ReadOnlyModelOutput -Raw $unknown -AgentId 'coordinator' -Manifest $manifest
Add-CaseResult 'EVAL_MODEL_OUTPUT_UNKNOWN_EXTRA_KEY_V1' ((-not $unknownResult.passed) -and ($unknownResult.reason -eq 'MODEL_OUTPUT_UNKNOWN_KEY=EXTRA_FIELD')) $unknownResult.reason

$duplicate=@"
ROLE=coordinator
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
"@
$duplicateResult=Test-ReadOnlyModelOutput -Raw $duplicate -AgentId 'coordinator' -Manifest $manifest
Add-CaseResult 'EVAL_MODEL_OUTPUT_DUPLICATE_KEY_V1' ((-not $duplicateResult.passed) -and ($duplicateResult.reason -eq 'MODEL_OUTPUT_DUPLICATE_KEY')) $duplicateResult.reason

$outDir=Join-Path $Root 'output/evals'; New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$stamp=[DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
$outPath=Join-Path $outDir "MODEL_OUTPUT_CONTRACT_ALIGNMENT_EVAL_REPORT_$stamp.json"
$passed=@($cases | Where-Object {$_.passed}).Count
$report=[ordered]@{report_id="MOCA-EVAL-$stamp";executed_at_utc=[DateTime]::UtcNow.ToString('o');mode='DETERMINISTIC_POLICY_ONLY';passed=$passed;total=$cases.Count;results=$cases;model_execution='NONE';platform_mutation='NONE';database_access='NONE'}
$report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $outPath -Encoding UTF8
"EVAL_CASE_COUNT=$($cases.Count)"
"EVAL_PASSED_COUNT=$passed"
"EVAL_FAILED_COUNT=$($cases.Count-$passed)"
"EVAL_REPORT_PATH=$outPath"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
if ($passed -eq $cases.Count) { 'FINAL_RESULT=PASS'; exit 0 }
'FINAL_RESULT=FAIL'
exit 1
