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

$registryPath = Join-Path $Target 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if (-not (Test-Path -LiteralPath $registryPath)) {
  throw "TARGET_REGISTRY_NOT_FOUND=$registryPath"
}

$copyPlan = @(
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1'; label = 'Add corrected Pack 01 V1.3 static validation' },
  @{ source = 'scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1'; target = 'scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1'; label = 'Add Pack 01 V1.3 preflight' },
  @{ source = 'governance\read_only_analysis_pack_01\STATIC_VALIDATION_SCOPE_CONTRACT_V1_3.md'; target = 'governance\read_only_analysis_pack_01\STATIC_VALIDATION_SCOPE_CONTRACT_V1_3.md'; label = 'Add V1.3 static validation scope contract' },
  @{ source = 'README_AR.md'; target = 'README_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_3_AR.md'; label = 'Add V1.3 Arabic readme' },
  @{ source = 'ROOT_CAUSE_AND_REMEDIATION_AR.md'; target = 'ROOT_CAUSE_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_3_AR.md'; label = 'Add V1.3 remediation note' },
  @{ source = 'MANIFEST.md'; target = 'MANIFEST_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_3.md'; label = 'Add V1.3 manifest' }
)

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source

  if (-not (Test-Path -LiteralPath $source)) {
    throw "PACKAGE_SOURCE_NOT_FOUND=$source"
  }
}

foreach ($entry in $copyPlan) {
  $source = Join-Path $SourceRoot $entry.source
  $destination = Join-Path $Target $entry.target
  $destinationDirectory = Split-Path -Parent $destination

  if ($PSCmdlet.ShouldProcess($destinationDirectory, 'Create V1.3 static-validation target directory when needed')) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destination, $entry.label)) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
}

"INSTALL_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"INSTALL_MODE=$Mode"
"PLAN_ENTRY_COUNT=$($copyPlan.Count)"
'REGISTRY_MUTATION=NONE'
'CORE_RUNTIME_MUTATION=NONE'
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'NEXT_STEP=RUN_V1_3_PREFLIGHT_STATIC_TEST_AND_PACK01_EVALS'
