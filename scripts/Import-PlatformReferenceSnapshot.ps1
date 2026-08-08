[CmdletBinding(SupportsShouldProcess)]
param(
  [Parameter(Mandatory = $true)]
  [string]$PlatformRoot,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$sourceDocs = Join-Path $PlatformRoot 'docs\ai'
$sourceAgents = Join-Path $PlatformRoot 'local_agents'
$destination = Join-Path $ProjectRoot 'reference_sources\platform_snapshot'

if (-not (Test-Path -LiteralPath $PlatformRoot)) { throw "PLATFORM_ROOT_NOT_FOUND" }
New-Item -ItemType Directory -Path $destination -Force | Out-Null

$copied = 0
foreach ($item in @(
  @{ Source = $sourceDocs; Name = 'docs_ai' },
  @{ Source = $sourceAgents; Name = 'local_agents' }
)) {
  if (-not (Test-Path -LiteralPath $item.Source)) {
    Write-Host "SOURCE_MISSING=$($item.Source)"
    continue
  }
  $target = Join-Path $destination $item.Name
  if ($PSCmdlet.ShouldProcess($target, 'Copy platform reference directory')) {
    Copy-Item -LiteralPath $item.Source -Destination $target -Recurse -Force
  }
  $copied += 1
}

Write-Host "REFERENCE_COPY_SCOPE=DOCS_AI_AND_LOCAL_AGENTS_ONLY"
Write-Host "PLATFORM_SOURCE_MUTATION=NONE"
Write-Host "DIRECTORY_COPY_COUNT=$copied"
Write-Host "NEXT_STEP=REVIEW_IMPORTED_REFERENCE"
