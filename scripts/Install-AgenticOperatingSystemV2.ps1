[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectRoot,

  [ValidateSet("New","Upgrade")]
  [string]$Mode = "Upgrade"
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $PSScriptRoot
$Target = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not (Test-Path -LiteralPath $PackageRoot)) {
  throw "PACKAGE_ROOT_NOT_FOUND=$PackageRoot"
}

if ($Mode -eq "New" -and (Test-Path -LiteralPath $Target)) {
  throw "TARGET_ALREADY_EXISTS_FOR_NEW_MODE=$Target"
}

if ($Mode -eq "Upgrade" -and -not (Test-Path -LiteralPath $Target)) {
  throw "TARGET_NOT_FOUND_FOR_UPGRADE_MODE=$Target"
}

$ControlledRoots = @(
  "agents",
  "governance",
  "skills",
  "task_contracts",
  "memory",
  "evals",
  "reference_sources\operating_manual"
)

$ControlledFiles = @(
  "README_AR.md",
  "PROJECT_STATUS_AR.md",
  "MIGRATION_FROM_V1_AR.md",
  "CHANGELOG_V2.md",
  "MANIFEST.md",
  ".env.example"
)

$PlanCount = 0

function Copy-ControlledDirectory {
  param(
    [string]$RelativePath
  )

  $SourcePath = Join-Path $PackageRoot $RelativePath
  $DestinationPath = Join-Path $Target $RelativePath

  if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "SOURCE_DIRECTORY_MISSING=$SourcePath"
  }

  if ($PSCmdlet.ShouldProcess($DestinationPath, "Copy controlled Local Agent V2 directory")) {
    New-Item -ItemType Directory -Force -Path $DestinationPath | Out-Null
    Copy-Item -LiteralPath (Join-Path $SourcePath "*") -Destination $DestinationPath -Recurse -Force
  }

  $script:PlanCount++
}

function Copy-ControlledFile {
  param(
    [string]$RelativePath
  )

  $SourcePath = Join-Path $PackageRoot $RelativePath
  $DestinationPath = Join-Path $Target $RelativePath

  if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "SOURCE_FILE_MISSING=$SourcePath"
  }

  if ($PSCmdlet.ShouldProcess($DestinationPath, "Copy controlled Local Agent V2 file")) {
    $Parent = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
  }

  $script:PlanCount++
}

if ($Mode -eq "New") {
  if ($PSCmdlet.ShouldProcess($Target, "Create Local Agent project root")) {
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
  }

  Get-ChildItem -LiteralPath $PackageRoot -Force | ForEach-Object {
    if ($_.Name -eq "scripts") {
      return
    }

    $DestinationPath = Join-Path $Target $_.Name
    if ($PSCmdlet.ShouldProcess($DestinationPath, "Copy Local Agent Foundation V2 item")) {
      Copy-Item -LiteralPath $_.FullName -Destination $DestinationPath -Recurse -Force
    }
    $PlanCount++
  }

  $SourceScripts = Join-Path $PackageRoot "scripts"
  $DestinationScripts = Join-Path $Target "scripts"
  if ($PSCmdlet.ShouldProcess($DestinationScripts, "Copy Local Agent Foundation V2 scripts")) {
    New-Item -ItemType Directory -Force -Path $DestinationScripts | Out-Null
    Copy-Item -LiteralPath (Join-Path $SourceScripts "*") -Destination $DestinationScripts -Recurse -Force
  }
  $PlanCount++
}
else {
  foreach ($RelativePath in $ControlledRoots) {
    Copy-ControlledDirectory -RelativePath $RelativePath
  }

  foreach ($RelativePath in $ControlledFiles) {
    Copy-ControlledFile -RelativePath $RelativePath
  }

  $SourceScripts = Join-Path $PackageRoot "scripts"
  $DestinationScripts = Join-Path $Target "scripts"
  foreach ($ScriptName in @("Install-AgenticOperatingSystemV2.ps1","Test-AgenticOperatingSystemV2.ps1","README_V2_AR.md")) {
    $SourceScript = Join-Path $SourceScripts $ScriptName
    $DestinationScript = Join-Path $DestinationScripts $ScriptName
    if (-not (Test-Path -LiteralPath $SourceScript)) {
      throw "SOURCE_SCRIPT_MISSING=$SourceScript"
    }
    if ($PSCmdlet.ShouldProcess($DestinationScript, "Copy Local Agent V2 script")) {
      New-Item -ItemType Directory -Force -Path $DestinationScripts | Out-Null
      Copy-Item -LiteralPath $SourceScript -Destination $DestinationScript -Force
    }
    $PlanCount++
  }
}

Write-Output "INSTALL_STATUS=COMPLETE"
Write-Output "INSTALL_MODE=$Mode"
Write-Output "PLAN_ENTRY_COUNT=$PlanCount"
Write-Output "AGENT_EXECUTION=DISABLED"
Write-Output "PLATFORM_MUTATION=NONE"
Write-Output "DATABASE_ACCESS=NONE"
Write-Output "NEXT_STEP=RUN_STATIC_TEST_ONLY"
