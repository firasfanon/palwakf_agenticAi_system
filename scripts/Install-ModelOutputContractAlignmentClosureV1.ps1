[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)] [string]$ProjectRoot,
  [ValidateSet('Upgrade')] [string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path -LiteralPath $Target -PathType Container)) { throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target" }

$Prerequisites = @(
  'runtime/ReadOnlyRuntimeContextEvidenceV1.psm1',
  'task_contracts/MODEL_OUTPUT_CONTRACT_V1.json',
  'scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'scripts/Test-ReadOnlyRuntimeContextEvidenceClosureV1.ps1'
)
$MissingPrerequisites = @($Prerequisites | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Target $_)) })
if ($MissingPrerequisites.Count -gt 0) {
  throw ('READ_ONLY_RUNTIME_CONTEXT_PREREQUISITES_MISSING=' + [string]::Join(',', $MissingPrerequisites))
}

$Copies = @(
  @{ Source='runtime/ReadOnlyRuntimeContextEvidenceV1.psm1'; Destination='runtime/ReadOnlyRuntimeContextEvidenceV1.psm1'; Action='Copy model-output contract alignment runtime module' },
  @{ Source='task_contracts/MODEL_OUTPUT_CONTRACT_V1.json'; Destination='task_contracts/MODEL_OUTPUT_CONTRACT_V1.json'; Action='Copy model-output contract alignment schema' },
  @{ Source='scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'; Destination='scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'; Action='Copy aligned read-only context runner' },
  @{ Source='scripts/Test-ModelOutputContractAlignmentClosureV1.ps1'; Destination='scripts/Test-ModelOutputContractAlignmentClosureV1.ps1'; Action='Copy alignment static test' },
  @{ Source='scripts/Invoke-ModelOutputContractAlignmentEvalsV1.ps1'; Destination='scripts/Invoke-ModelOutputContractAlignmentEvalsV1.ps1'; Action='Copy alignment deterministic evals' },
  @{ Source='governance/model_output_contract_alignment/MODEL_OUTPUT_CONTRACT_ALIGNMENT_POLICY_V1.md'; Destination='governance/model_output_contract_alignment/MODEL_OUTPUT_CONTRACT_ALIGNMENT_POLICY_V1.md'; Action='Copy alignment policy' },
  @{ Source='ROOT_CAUSE_AND_REMEDIATION_AR.md'; Destination='ROOT_CAUSE_AND_REMEDIATION_AR.md'; Action='Copy root cause record' },
  @{ Source='README_AR.md'; Destination='README_MODEL_OUTPUT_CONTRACT_ALIGNMENT_V1_AR.md'; Action='Copy package readme' },
  @{ Source='MANIFEST.md'; Destination='MANIFEST_MODEL_OUTPUT_CONTRACT_ALIGNMENT_V1.md'; Action='Copy package manifest' }
)
$planCount=0
foreach ($item in $Copies) {
  $source=Join-Path $PackageRoot $item.Source
  $destination=Join-Path $Target $item.Destination
  if ($PSCmdlet.ShouldProcess($destination, $item.Action)) {
    $parent=Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
  $planCount++
}
'INSTALL_STATUS=COMPLETE'
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$planCount"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'NEXT_STEP=RUN_ALIGNMENT_TESTS_AND_EVALS_ONLY'
