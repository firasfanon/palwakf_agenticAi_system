[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$required = @(
  'runtime/ReadOnlyRuntimeContextEvidenceV1.psm1',
  'task_contracts/MODEL_OUTPUT_CONTRACT_V1.json',
  'scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts/Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1'
)

$missing = @()

foreach ($relative in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
    $missing += $relative
  }
}

$contract = Get-Content `
  -LiteralPath (Join-Path $Root 'task_contracts/MODEL_OUTPUT_CONTRACT_V1.json') `
  -Raw `
  -Encoding UTF8 |
  ConvertFrom-Json

$requiredKeys = @($contract.required_keys)
$forbiddenKeys = @($contract.forbidden_keys)

$runner = Get-Content `
  -LiteralPath (Join-Path $Root 'scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1') `
  -Raw `
  -Encoding UTF8

$contractKeyCountPass = ($requiredKeys.Count -eq 11)
$taskIdForbiddenPass = ($forbiddenKeys -contains 'TASK_ID')
$additionalKeysPass = ($contract.additional_keys_allowed -eq $false)

# Exact case-sensitive literal check.
# This prevents the valid internal metadata field "task_id=$TaskId"
# from being treated as the forbidden model-output field "TASK_ID=$TaskId".
$oldPromptPatternAbsent = (-not $runner.Contains('TASK_ID=$TaskId'))

$newPromptGuardPresent = (
  $runner -match [regex]::Escape('The output field TASK_ID is forbidden.')
)

$exactTemplatePresent = (
  $runner -match [regex]::Escape('EXACT_OUTPUT_TEMPLATE:')
)

"REQUIRED_ITEM_COUNT=$($required.Count)"
"MISSING_ITEM_COUNT=$($missing.Count)"
"MODEL_OUTPUT_REQUIRED_KEY_COUNT=$($requiredKeys.Count)"
"ADDITIONAL_KEYS_ALLOWED=$($contract.additional_keys_allowed)"
"TASK_ID_FORBIDDEN=$taskIdForbiddenPass"
"OLD_TASK_ID_KEY_VALUE_CONTEXT_PRESENT=$(-not $oldPromptPatternAbsent)"
"EXACT_TEMPLATE_GUARD_PRESENT=$newPromptGuardPresent"
"EXACT_TEMPLATE_MARKER_PRESENT=$exactTemplatePresent"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if (
  $missing.Count -eq 0 -and
  $contractKeyCountPass -and
  $taskIdForbiddenPass -and
  $additionalKeysPass -and
  $oldPromptPatternAbsent -and
  $newPromptGuardPresent -and
  $exactTemplatePresent
) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
