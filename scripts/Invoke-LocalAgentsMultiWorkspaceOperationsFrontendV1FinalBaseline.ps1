param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $false)][string]$OutputRoot
)

$ErrorActionPreference = 'Stop'

function Get-RelativeProjectPath {
  param(
    [Parameter(Mandatory = $true)][string]$FullPath,
    [Parameter(Mandatory = $true)][string]$RootPath
  )

  $normalizedRoot = [System.IO.Path]::GetFullPath($RootPath)
  $trimChars = [char[]]@([char]92, [char]47)
  $normalizedRoot = $normalizedRoot.TrimEnd($trimChars)
  $normalizedFullPath = [System.IO.Path]::GetFullPath($FullPath)

  if ($normalizedFullPath.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $normalizedFullPath.Substring($normalizedRoot.Length).TrimStart($trimChars)
  }

  return $normalizedFullPath
}

function Add-InventoryRow {
  param(
    [AllowNull()][object]$Target,
    [Parameter(Mandatory = $true)][object]$Row
  )

  # PowerShell 5.1 can reject a mandatory collection parameter when the
  # supplied ArrayList is empty. Keep Target scalar and validate explicitly.
  if ($null -eq $Target) {
    throw 'INVENTORY_TARGET_NULL'
  }
  if (-not ($Target -is [System.Collections.IList])) {
    throw ('INVENTORY_TARGET_NOT_I_LIST={0}' -f $Target.GetType().FullName)
  }

  [void]$Target.Add($Row)
}

if (-not (Test-Path -LiteralPath $PackageRoot -PathType Container)) {
  throw ('PACKAGE_ROOT_NOT_FOUND={0}' -f $PackageRoot)
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw ('PROJECT_ROOT_NOT_FOUND={0}' -f $ProjectRoot)
}

$resolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$srcRoot = Join-Path $resolvedProjectRoot 'backend/src/palwakf_local_agents'
$appPath = Join-Path $srcRoot 'app.py'
if (-not (Test-Path -LiteralPath $appPath -PathType Leaf)) {
  throw ('APP_ENTRYPOINT_NOT_FOUND={0}' -f $appPath)
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
  $tempBase = [System.IO.Path]::GetTempPath()
  $stamp = Get-Date -Format 'yyyyMMdd_HHmmssfff'
  $OutputRoot = Join-Path $tempBase ('local_agents_frontend_v1_final_baseline_{0}' -f $stamp)
}

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$evidenceRoot = [System.IO.Path]::GetFullPath($OutputRoot)

$staticRootList = New-Object System.Collections.ArrayList
$assetRows = New-Object System.Collections.ArrayList
$routeRows = New-Object System.Collections.ArrayList
$frameworkRows = New-Object System.Collections.ArrayList
$fetchRows = New-Object System.Collections.ArrayList

if (Test-Path -LiteralPath $srcRoot -PathType Container) {
  $candidateStaticRoots = @(Get-ChildItem -LiteralPath $srcRoot -Directory -Recurse -ErrorAction Stop | Sort-Object FullName)
  foreach ($candidateRoot in $candidateStaticRoots) {
    $indexPath = Join-Path $candidateRoot.FullName 'index.html'
    if (($candidateRoot.Name -eq 'static') -and (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
      [void]$staticRootList.Add($candidateRoot.FullName)
    }
  }
}

foreach ($staticRoot in $staticRootList.ToArray()) {
  $staticRootRelative = Get-RelativeProjectPath -FullPath $staticRoot -RootPath $resolvedProjectRoot
  $staticFiles = @(Get-ChildItem -LiteralPath $staticRoot -File -Recurse -Force -ErrorAction Stop | Sort-Object FullName)
  foreach ($staticFile in $staticFiles) {
    $relativePath = Get-RelativeProjectPath -FullPath $staticFile.FullName -RootPath $resolvedProjectRoot
    Add-InventoryRow -Target $assetRows -Row ([pscustomobject]@{
      static_root = $staticRootRelative
      relative_path = $relativePath
      bytes = [Int64]$staticFile.Length
      sha256 = (Get-FileHash -LiteralPath $staticFile.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
      extension = [string]$staticFile.Extension
    })
  }
}

$pythonFiles = @()
if (Test-Path -LiteralPath $srcRoot -PathType Container) {
  $pythonFiles = @(Get-ChildItem -LiteralPath $srcRoot -Filter '*.py' -File -Recurse -ErrorAction Stop | Sort-Object FullName)
}
$routePattern = '(?m)^\s*@(?:[A-Za-z_][A-Za-z0-9_]*\.)?(?<method>get|post|put|patch|delete)\(\s*["''](?<path>[^"'']+)'
foreach ($pythonFile in $pythonFiles) {
  $text = Get-Content -LiteralPath $pythonFile.FullName -Raw -Encoding UTF8 -ErrorAction Stop
  $matches = [System.Text.RegularExpressions.Regex]::Matches($text, $routePattern)
  foreach ($match in $matches) {
    Add-InventoryRow -Target $routeRows -Row ([pscustomobject]@{
      file = Get-RelativeProjectPath -FullPath $pythonFile.FullName -RootPath $resolvedProjectRoot
      method = $match.Groups['method'].Value.ToUpperInvariant()
      route = $match.Groups['path'].Value
    })
  }
}

$frameworkNames = @('package.json', 'vite.config.js', 'vite.config.ts', 'webpack.config.js', 'webpack.config.ts', 'angular.json', 'next.config.js', 'next.config.mjs')
$allFiles = @(Get-ChildItem -LiteralPath $resolvedProjectRoot -File -Recurse -ErrorAction Stop | Sort-Object FullName)
foreach ($projectFile in $allFiles) {
  if ($frameworkNames -contains $projectFile.Name) {
    $kind = if ($projectFile.Name -eq 'package.json') { 'package_manifest' } else { 'framework_config' }
    Add-InventoryRow -Target $frameworkRows -Row ([pscustomobject]@{
      file = Get-RelativeProjectPath -FullPath $projectFile.FullName -RootPath $resolvedProjectRoot
      kind = $kind
      sha256 = (Get-FileHash -LiteralPath $projectFile.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
    })
  }
}

foreach ($assetRow in $assetRows.ToArray()) {
  if (@('.js', '.mjs', '.ts') -contains $assetRow.extension) {
    $assetAbsolutePath = Join-Path $resolvedProjectRoot $assetRow.relative_path
    if (Test-Path -LiteralPath $assetAbsolutePath -PathType Leaf) {
      $assetText = Get-Content -LiteralPath $assetAbsolutePath -Raw -Encoding UTF8 -ErrorAction Stop
      $fetchMatches = [System.Text.RegularExpressions.Regex]::Matches($assetText, '(?m)fetch\(\s*["''](?<url>[^"'']+)')
      foreach ($fetchMatch in $fetchMatches) {
        Add-InventoryRow -Target $fetchRows -Row ([pscustomobject]@{
          file = [string]$assetRow.relative_path
          url = $fetchMatch.Groups['url'].Value
        })
      }
    }
  }
}

$knownWorkspaceStatic = Join-Path $resolvedProjectRoot 'backend/src/palwakf_local_agents/workspace_core/static'
$knownWorkspaceStaticState = if (Test-Path -LiteralPath $knownWorkspaceStatic -PathType Container) { 'PRESENT' } else { 'MISSING' }
$staticMode = if ($knownWorkspaceStaticState -eq 'PRESENT') {
  'STATIC_WORKSPACE_CORE_CONFIRMED'
} elseif ($staticRootList.Count -gt 0) {
  'STATIC_FRONTEND_ROOTS_FOUND'
} else {
  'STATIC_ROOT_NOT_CONFIRMED'
}
$frameworkMode = if ($frameworkRows.Count -eq 0) { 'NO_FRONTEND_FRAMEWORK_CONFIG_DISCOVERED' } else { 'FRAMEWORK_CONFIG_DISCOVERED_REQUIRES_BINDING' }

$staticRootRelativeList = New-Object System.Collections.ArrayList
foreach ($staticRoot in $staticRootList.ToArray()) {
  [void]$staticRootRelativeList.Add((Get-RelativeProjectPath -FullPath $staticRoot -RootPath $resolvedProjectRoot))
}

$baseline = [pscustomobject]@{
  contract = 'LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_FINAL_BASELINE'
  package_id = 'PALWAKF_LOCAL_AGENTS_FRONTEND_V1_BASELINE_CARRIER_EMPTY_COLLECTION_BINDING_REPAIR_CANDIDATE'
  generated_at = (Get-Date).ToString('o')
  project_root = $resolvedProjectRoot
  project_root_hash_anchor = (Get-FileHash -LiteralPath $appPath -Algorithm SHA256 -ErrorAction Stop).Hash
  known_workspace_static_root = $knownWorkspaceStatic
  known_workspace_static_state = $knownWorkspaceStaticState
  static_frontend_mode = $staticMode
  framework_mode = $frameworkMode
  static_roots = [object[]]$staticRootRelativeList.ToArray()
  assets = [object[]]$assetRows.ToArray()
  route_inventory = [object[]]($routeRows.ToArray() | Sort-Object route, method, file)
  frontend_framework_inventory = [object[]]($frameworkRows.ToArray() | Sort-Object file)
  fetch_inventory = [object[]]($fetchRows.ToArray() | Sort-Object file, url)
  execution_boundaries = [pscustomobject]@{
    project_mutation = 'NONE'
    model_execution = 'NONE'
    pilot_execution = 'NOT_EXECUTED'
    service_start = 'NONE'
    shell_execution = 'NONE'
    git_write = 'NONE'
    external_network = 'NONE'
  }
}

$jsonPath = Join-Path $evidenceRoot 'frontend_final_baseline.json'
$markdownPath = Join-Path $evidenceRoot 'frontend_final_baseline.md'
$zipPath = "$evidenceRoot.zip"

$baselineJson = $baseline | ConvertTo-Json -Depth 24
Set-Content -LiteralPath $jsonPath -Value $baselineJson -Encoding UTF8 -ErrorAction Stop

$markdownLines = New-Object System.Collections.ArrayList
[void]$markdownLines.Add('# Local Agents Multi-Workspace Operations Frontend V1 Final Baseline')
[void]$markdownLines.Add('')
[void]$markdownLines.Add(('- Generated at: {0}' -f $baseline.generated_at))
[void]$markdownLines.Add(('- Static frontend mode: {0}' -f $staticMode))
[void]$markdownLines.Add(('- Framework mode: {0}' -f $frameworkMode))
[void]$markdownLines.Add(('- Known workspace static root: {0}' -f $knownWorkspaceStaticState))
[void]$markdownLines.Add(('- Static roots: {0}' -f $staticRootList.Count))
[void]$markdownLines.Add(('- Static assets: {0}' -f $assetRows.Count))
[void]$markdownLines.Add(('- API routes discovered: {0}' -f $routeRows.Count))
[void]$markdownLines.Add(('- Fetch calls discovered: {0}' -f $fetchRows.Count))
[void]$markdownLines.Add(('- Framework config files: {0}' -f $frameworkRows.Count))
[void]$markdownLines.Add('')
[void]$markdownLines.Add('## Execution boundary')
[void]$markdownLines.Add('- Project mutation: NONE')
[void]$markdownLines.Add('- Model execution: NONE')
[void]$markdownLines.Add('- Pilot execution: NOT_EXECUTED')
[void]$markdownLines.Add('- Service start: NONE')
[void]$markdownLines.Add('- Shell execution: NONE')
[void]$markdownLines.Add('- Git write: NONE')
[void]$markdownLines.Add('- External network: NONE')
Set-Content -LiteralPath $markdownPath -Value ([string[]]$markdownLines.ToArray()) -Encoding UTF8 -ErrorAction Stop

Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $evidenceRoot '*') -DestinationPath $zipPath -Force -ErrorAction Stop

'===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 FINAL BASELINE ====='
('KNOWN_WORKSPACE_STATIC_ROOT_STATE={0}' -f $knownWorkspaceStaticState)
('STATIC_FRONTEND_MODE={0}' -f $staticMode)
('FRAMEWORK_MODE={0}' -f $frameworkMode)
('STATIC_ROOT_COUNT={0}' -f $staticRootList.Count)
('STATIC_ASSET_COUNT={0}' -f $assetRows.Count)
('ROUTE_INVENTORY_COUNT={0}' -f $routeRows.Count)
('FETCH_INVENTORY_COUNT={0}' -f $fetchRows.Count)
('FRONTEND_FRAMEWORK_CONFIG_COUNT={0}' -f $frameworkRows.Count)
('BASELINE_MANIFEST={0}' -f $jsonPath)
('BASELINE_REPORT_MARKDOWN={0}' -f $markdownPath)
('EVIDENCE_ARCHIVE={0}' -f $zipPath)
'PROJECT_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SERVICE_START=NONE'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'EXTERNAL_NETWORK=NONE'
'BASELINE_RESULT=PASS'
