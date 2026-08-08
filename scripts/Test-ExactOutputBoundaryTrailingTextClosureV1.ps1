[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$required = @(
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1'
)

$missing = @()

foreach ($relative in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missing += $relative
  }
}

$contract = Get-Content `
  -LiteralPath (Join-Path $Root 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json') `
  -Raw `
  -Encoding UTF8 |
  ConvertFrom-Json

$runner = Get-Content `
  -LiteralPath (Join-Path $Root 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1') `
  -Raw `
  -Encoding UTF8

$requiredKeyCountPass = (@($contract.required_keys).Count -eq 11)
$boundaryStartPass = ($contract.boundary_start -eq 'OUTPUT_CONTRACT_START')
$boundaryEndPass = ($contract.boundary_end -eq 'OUTPUT_CONTRACT_END')
$lineCountPass = ($contract.expected_line_count_including_boundaries -eq 13)
$trailingTextRejectedPass = ($contract.require_no_text_after_end -eq $true)
$taskIdForbiddenPass = (@($contract.forbidden_keys) -contains 'TASK_ID')
$oldTaskIdPromptLiteralAbsent = (-not $runner.Contains('TASK_ID=$TaskId'))
$finalOutputLockPresent = $runner.Contains('FINAL OUTPUT LOCK')
$templateStartPresent = $runner.Contains('OUTPUT_CONTRACT_START')
$templateEndPresent = $runner.Contains('OUTPUT_CONTRACT_END')
$noReferenceRepeatInstructionPresent = $runner.Contains('Do not repeat reference paths, snippet identifiers, or reference content.')

"REQUIRED_ITEM_COUNT=$($required.Count)"
"MISSING_ITEM_COUNT=$($missing.Count)"
"MODEL_OUTPUT_REQUIRED_KEY_COUNT=$(@($contract.required_keys).Count)"
"BOUNDARY_START=$($contract.boundary_start)"
"BOUNDARY_END=$($contract.boundary_end)"
"EXPECTED_LINE_COUNT=$($contract.expected_line_count_including_boundaries)"
"TRAILING_TEXT_REJECTED=$trailingTextRejectedPass"
"TASK_ID_FORBIDDEN=$taskIdForbiddenPass"
"OLD_TASK_ID_KEY_VALUE_CONTEXT_PRESENT=$(-not $oldTaskIdPromptLiteralAbsent)"
"FINAL_OUTPUT_LOCK_PRESENT=$finalOutputLockPresent"
"NO_REFERENCE_REPEAT_INSTRUCTION_PRESENT=$noReferenceRepeatInstructionPresent"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if (
  $missing.Count -eq 0 -and
  $requiredKeyCountPass -and
  $boundaryStartPass -and
  $boundaryEndPass -and
  $lineCountPass -and
  $trailingTextRejectedPass -and
  $taskIdForbiddenPass -and
  $oldTaskIdPromptLiteralAbsent -and
  $finalOutputLockPresent -and
  $templateStartPresent -and
  $templateEndPresent -and
  $noReferenceRepeatInstructionPresent
) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
