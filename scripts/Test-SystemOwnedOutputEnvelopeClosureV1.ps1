[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$ProjectRoot)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$required = @(
  'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1',
  'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json',
  'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts\Invoke-SystemOwnedOutputEnvelopeEvalsV1.ps1'
)

$missing = @()
foreach ($relative in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) { $missing += $relative }
}

$contract = Get-Content -LiteralPath (Join-Path $Root 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$runner = Get-Content -LiteralPath (Join-Path $Root 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1') -Raw -Encoding UTF8

Import-Module (Join-Path $Root 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1') -Force
$runtimeFunctions = @(
  'New-ReferenceEvidenceManifest',
  'Test-ReadOnlyModelOutputV1',
  'Get-CanonicalModelOutputEnvelopeV1'
)
$missingRuntimeFunctions = @()
foreach ($name in $runtimeFunctions) {
  if ($null -eq (Get-Command -Name $name -ErrorAction SilentlyContinue)) { $missingRuntimeFunctions += $name }
}

$keyCountPass = (@($contract.required_keys).Count -eq 11)
$lineCountPass = ($contract.expected_model_body_line_count -eq 11)
$envelopeEnabledPass = ($contract.system_owned_envelope.enabled -eq $true)
$startPass = ($contract.system_owned_envelope.start -eq 'OUTPUT_CONTRACT_START')
$endPass = ($contract.system_owned_envelope.end -eq 'OUTPUT_CONTRACT_END')
$boundaryForbiddenPass = (
  @($contract.forbidden_keys) -contains 'OUTPUT_CONTRACT_START' -and
  @($contract.forbidden_keys) -contains 'OUTPUT_CONTRACT_END'
)
$bodyLockPass = $runner.Contains('MODEL BODY OUTPUT LOCK')
$hostOwnsBoundaryPass = $runner.Contains('The host creates those boundaries only after deterministic validation.')
$executeModePass = $runner.Contains('$runMode = ''READ_ONLY_CONTEXT_EVIDENCE_MODEL_RUN''')
$rawArtifactPass = $runner.Contains('RAW_OUTPUT_PATH=')
$canonicalArtifactPass = $runner.Contains('CANONICAL_OUTPUT_PATH=')
$canonicalAfterValidationPass = $runner.Contains('$canonicalOutput = $validation.canonical_output')

"REQUIRED_ITEM_COUNT=$($required.Count)"
"MISSING_ITEM_COUNT=$($missing.Count)"
"RUNTIME_REQUIRED_FUNCTION_COUNT=$($runtimeFunctions.Count)"
"MISSING_RUNTIME_FUNCTION_COUNT=$($missingRuntimeFunctions.Count)"
"MISSING_RUNTIME_FUNCTIONS=$([string]::Join(',', $missingRuntimeFunctions))"
"MODEL_OUTPUT_REQUIRED_KEY_COUNT=$(@($contract.required_keys).Count)"
"MODEL_BODY_EXPECTED_LINE_COUNT=$($contract.expected_model_body_line_count)"
"SYSTEM_OWNED_ENVELOPE_ENABLED=$($contract.system_owned_envelope.enabled)"
"ENVELOPE_START=$($contract.system_owned_envelope.start)"
"ENVELOPE_END=$($contract.system_owned_envelope.end)"
"BOUNDARY_FIELDS_FORBIDDEN_IN_MODEL_OUTPUT=$boundaryForbiddenPass"
"MODEL_BODY_OUTPUT_LOCK_PRESENT=$bodyLockPass"
"HOST_OWNS_BOUNDARIES_INSTRUCTION_PRESENT=$hostOwnsBoundaryPass"
"EXECUTE_RUN_MODE_PRESENT=$executeModePass"
"RAW_OUTPUT_ARTIFACT_PRESENT=$rawArtifactPass"
"CANONICAL_OUTPUT_ARTIFACT_PRESENT=$canonicalArtifactPass"
"CANONICAL_CREATED_AFTER_VALIDATION_PRESENT=$canonicalAfterValidationPass"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if (
  $missing.Count -eq 0 -and
  $missingRuntimeFunctions.Count -eq 0 -and
  $keyCountPass -and
  $lineCountPass -and
  $envelopeEnabledPass -and
  $startPass -and
  $endPass -and
  $boundaryForbiddenPass -and
  $bodyLockPass -and
  $hostOwnsBoundaryPass -and
  $executeModePass -and
  $rawArtifactPass -and
  $canonicalArtifactPass -and
  $canonicalAfterValidationPass
) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
