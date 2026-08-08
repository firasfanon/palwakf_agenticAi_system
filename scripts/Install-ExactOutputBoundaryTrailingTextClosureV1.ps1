[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,

  [ValidateSet('Upgrade')]
  [string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not (Test-Path -LiteralPath $Target)) {
  throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target"
}

$copyPlan = @(
  @{ source = 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'; target = 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'; label = 'Copy exact-output runtime module' },
  @{ source = 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'; target = 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'; label = 'Copy exact-output contract schema' },
  @{ source = 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'; target = 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'; label = 'Copy exact-output read-only runner' },
  @{ source = 'scripts\Test-ExactOutputBoundaryTrailingTextClosureV1.ps1'; target = 'scripts\Test-ExactOutputBoundaryTrailingTextClosureV1.ps1'; label = 'Copy exact-output static test' },
  @{ source = 'scripts\Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1'; target = 'scripts\Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1'; label = 'Copy exact-output deterministic evals' },
  @{ source = 'governance\exact_output_boundary\EXACT_OUTPUT_BOUNDARY_AND_TRAILING_TEXT_POLICY_V1.md'; target = 'governance\exact_output_boundary\EXACT_OUTPUT_BOUNDARY_AND_TRAILING_TEXT_POLICY_V1.md'; label = 'Copy exact-output governance policy' },
  @{ source = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'; target = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'; label = 'Copy root-cause record' },
  @{ source = 'README_AR.md'; target = 'README_EXACT_OUTPUT_BOUNDARY_TRAILING_TEXT_CLOSURE_V1_AR.md'; label = 'Copy package readme' },
  @{ source = 'MANIFEST.md'; target = 'MANIFEST_EXACT_OUTPUT_BOUNDARY_TRAILING_TEXT_CLOSURE_V1.md'; label = 'Copy package manifest' }
)

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if (-not (Test-Path -LiteralPath $source)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$source"
  }

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, $entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

'INSTALL_STATUS=COMPLETE'
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count)"
'AGENT_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'NEXT_STEP=RUN_EXACT_OUTPUT_STATIC_TEST_AND_EVALS_ONLY'
