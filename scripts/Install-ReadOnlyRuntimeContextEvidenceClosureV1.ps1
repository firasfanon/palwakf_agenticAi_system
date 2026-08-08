[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)] [string]$ProjectRoot,
  [ValidateSet('Upgrade')] [string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path -LiteralPath $Target -PathType Container)) { throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target" }
$Prerequisites = @('agents/registry/AGENT_SKILL_ASSIGNMENTS_V1.json','scripts/Set-HumanApprovalV1.ps1','tasks/approved','reference_sources/approved')
$MissingPrerequisites = @($Prerequisites | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Target $_)) })
if ($MissingPrerequisites.Count -gt 0) { throw ('OPERATIONAL_ACTIVATION_PREREQUISITES_MISSING=' + [string]::Join(',', $MissingPrerequisites)) }

$DirectorySources = @(
  'governance/read_only_runtime_context_evidence',
  'task_contracts',
  'templates',
  'evals/read_only_runtime_context_evidence',
  'tasks/templates',
  'runtime',
  'reference_sources/approved'
)
$RootFiles = @('README_AR.md','PROJECT_STATUS_AR.md','CHANGELOG_V1.md','MIGRATION_FROM_OPERATIONAL_ACTIVATION_V1_AR.md','MANIFEST.md')
$ScriptFiles = @(
  'Install-ReadOnlyRuntimeContextEvidenceClosureV1.ps1',
  'Test-ReadOnlyRuntimeContextEvidenceClosureV1.ps1',
  'New-ReadOnlyEvidenceTaskV1.ps1',
  'New-ReadOnlyEvidencePilotV1.ps1',
  'Invoke-ReadOnlyEvidenceGatewayV1.ps1',
  'Invoke-ReadOnlyContextEvidenceRunnerV1.ps1',
  'Invoke-ReadOnlyRuntimeContextEvidenceEvalsV1.ps1'
)
$RuntimeDirectories = @('output/evidence_manifests','output/read_only_context_runs','runtime/context','audit')
$planCount = 0
foreach ($relative in $DirectorySources) {
  $source = Join-Path $PackageRoot $relative
  $destination = Join-Path $Target $relative
  if ($PSCmdlet.ShouldProcess($destination, 'Copy controlled read-only runtime context directory')) {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $source '*') -Destination $destination -Recurse -Force
  }
  $planCount++
}
foreach ($relative in $RuntimeDirectories) {
  $destination = Join-Path $Target $relative
  if ($PSCmdlet.ShouldProcess($destination, 'Create read-only runtime context directory')) { New-Item -ItemType Directory -Path $destination -Force | Out-Null }
  $planCount++
}
foreach ($file in $RootFiles) {
  $source = Join-Path $PackageRoot $file
  $destination = Join-Path $Target $file
  if ($PSCmdlet.ShouldProcess($destination, 'Copy controlled read-only runtime context file')) { Copy-Item -LiteralPath $source -Destination $destination -Force }
  $planCount++
}
$targetScripts = Join-Path $Target 'scripts'
foreach ($file in $ScriptFiles) {
  $source = Join-Path $PackageRoot (Join-Path 'scripts' $file)
  $destination = Join-Path $targetScripts $file
  if ($PSCmdlet.ShouldProcess($destination, 'Copy controlled read-only runtime context script')) {
    New-Item -ItemType Directory -Path $targetScripts -Force | Out-Null
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
'NEXT_STEP=RUN_STATIC_TEST_AND_CONTEXT_EVALS_ONLY'
