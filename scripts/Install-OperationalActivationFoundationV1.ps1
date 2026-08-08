[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,
  [ValidateSet('Upgrade','New')]
  [string]$Mode = 'Upgrade'
)

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)

if ($Mode -eq 'Upgrade' -and -not (Test-Path -LiteralPath $Target -PathType Container)) {
  throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target"
}
if ($Mode -eq 'New' -and (Test-Path -LiteralPath $Target)) {
  throw "TARGET_ALREADY_EXISTS_FOR_NEW_MODE=$Target"
}

$DirectorySources = @(
  'agents/registry',
  'skills/registry',
  'governance/operational_activation',
  'task_contracts',
  'templates',
  'evals/cases'
)
$RootFiles = @('README_AR.md','PROJECT_STATUS_AR.md','CHANGELOG_V1.md','MANIFEST.md','.env.example')
$ScriptFiles = @(
  'Install-OperationalActivationFoundationV1.ps1',
  'Test-OperationalActivationFoundationV1.ps1',
  'New-LocalAgentTaskV1.ps1',
  'Set-HumanApprovalV1.ps1',
  'Invoke-ReadOnlyToolGatewayV1.ps1',
  'Invoke-ReadOnlyTaskRunnerV1.ps1',
  'Invoke-AgentEvalsV1.ps1'
)
$RuntimeDirectories = @(
  'tasks/inbox','tasks/approved','tasks/rejected','output/read_only_runs',
  'memory/pending','memory/approved','memory/rejected','audit','runtime','reference_sources/approved'
)
$planCount = 0

if ($Mode -eq 'New') {
  if ($PSCmdlet.ShouldProcess($Target, 'Create Local Agent project root')) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
  }
  $planCount++
}

foreach ($relative in $DirectorySources) {
  $source = Join-Path $PackageRoot $relative
  $destination = Join-Path $Target $relative
  if ($PSCmdlet.ShouldProcess($destination, 'Copy controlled operational activation directory')) {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $source '*') -Destination $destination -Recurse -Force
  }
  $planCount++
}
foreach ($relative in $RuntimeDirectories) {
  $destination = Join-Path $Target $relative
  if ($PSCmdlet.ShouldProcess($destination, 'Create operational runtime directory when needed')) {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
  }
  $planCount++
}
foreach ($file in $RootFiles) {
  $source = Join-Path $PackageRoot $file
  $destination = Join-Path $Target $file
  if ($PSCmdlet.ShouldProcess($destination, 'Copy controlled operational activation file')) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
  }
  $planCount++
}
$targetScripts = Join-Path $Target 'scripts'
foreach ($file in $ScriptFiles) {
  $source = Join-Path $PackageRoot (Join-Path 'scripts' $file)
  $destination = Join-Path $targetScripts $file
  if ($PSCmdlet.ShouldProcess($destination, 'Copy operational activation script')) {
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
'NEXT_STEP=RUN_STATIC_TEST_AND_EVALS_ONLY'
