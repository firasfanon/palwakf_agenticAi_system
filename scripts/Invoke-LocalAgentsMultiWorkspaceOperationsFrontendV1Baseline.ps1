param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw ('PROJECT_ROOT_NOT_FOUND={0}' -f $ProjectRoot)
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$evidenceRoot = Join-Path $env:TEMP ('local_agents_multi_workspace_operations_frontend_v1_baseline_{0}' -f $stamp)
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$srcRoot = Join-Path $ProjectRoot 'backend/src/palwakf_local_agents'
$staticRoots = @()
if (Test-Path -LiteralPath $srcRoot -PathType Container) {
  $staticRoots = @(
    Get-ChildItem -LiteralPath $srcRoot -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -eq 'static' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'index.html') -PathType Leaf)
    }
  )
}

$knownWorkspaceStatic = Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/workspace_core/static'
$knownWorkspaceStaticState = if (Test-Path -LiteralPath $knownWorkspaceStatic -PathType Container) { 'PRESENT' } else { 'MISSING' }

$assetRows = New-Object System.Collections.Generic.List[object]
foreach ($root in $staticRoots) {
  $rootRelative = $root.FullName.Substring($ProjectRoot.Length).TrimStart('\')
  $files = @(
    Get-ChildItem -LiteralPath $root.FullName -File -Recurse -Force |
    Sort-Object FullName
  )
  foreach ($file in $files) {
    $relative = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\')
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    [void]$assetRows.Add([pscustomobject]@{
      static_root = $rootRelative
      relative_path = $relative
      bytes = $file.Length
      sha256 = $hash
      extension = $file.Extension
    })
  }
}

$pythonFiles = @()
if (Test-Path -LiteralPath $srcRoot -PathType Container) {
  $pythonFiles = @(
    Get-ChildItem -LiteralPath $srcRoot -Filter '*.py' -File -Recurse -ErrorAction SilentlyContinue
  )
}

$routeRows = New-Object System.Collections.Generic.List[object]
$routePattern = '(?m)^\s*@(?:[A-Za-z_][A-Za-z0-9_]*\.)?(?<method>get|post|put|patch|delete)\(\s*["''](?<path>[^"'']+)'
foreach ($file in $pythonFiles) {
  $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
  foreach ($match in [regex]::Matches($text, $routePattern)) {
    [void]$routeRows.Add([pscustomobject]@{
      file = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\')
      method = $match.Groups['method'].Value.ToUpperInvariant()
      route = $match.Groups['path'].Value
    })
  }
}

$packageFiles = @(
  Get-ChildItem -LiteralPath $ProjectRoot -File -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -in @('package.json', 'vite.config.js', 'vite.config.ts', 'webpack.config.js', 'angular.json') }
)

$frameworkRows = New-Object System.Collections.Generic.List[object]
foreach ($file in $packageFiles) {
  $relative = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\')
  $kind = if ($file.Name -eq 'package.json') { 'package_manifest' } else { 'framework_config' }
  [void]$frameworkRows.Add([pscustomobject]@{
    file = $relative
    kind = $kind
    sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
  })
}

$fetchRows = New-Object System.Collections.Generic.List[object]
foreach ($asset in $assetRows | Where-Object { $_.extension -in @('.js', '.mjs', '.ts') }) {
  $absolute = Join-Path $ProjectRoot $asset.relative_path
  if (Test-Path -LiteralPath $absolute -PathType Leaf) {
    $text = Get-Content -LiteralPath $absolute -Raw -Encoding UTF8
    foreach ($match in [regex]::Matches($text, '(?m)fetch\(\s*["''](?<url>[^"'']+)')) {
      [void]$fetchRows.Add([pscustomobject]@{
        file = $asset.relative_path
        url = $match.Groups['url'].Value
      })
    }
  }
}

$staticMode = if ($knownWorkspaceStaticState -eq 'PRESENT') { 'STATIC_WORKSPACE_CORE_CONFIRMED' } elseif ($staticRoots.Count -gt 0) { 'STATIC_FRONTEND_ROOTS_FOUND' } else { 'STATIC_ROOT_NOT_CONFIRMED' }
$frameworkMode = if ($frameworkRows.Count -eq 0) { 'NO_FRONTEND_FRAMEWORK_CONFIG_DISCOVERED' } else { 'FRAMEWORK_CONFIG_DISCOVERED_REQUIRES_BINDING' }

$baseline = [pscustomobject]@{
  contract = 'LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_BASELINE'
  package_id = 'PALWAKF_LOCAL_AGENTS_MEGA_BATCH_LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_DESIGN_BASELINE_CANDIDATE'
  generated_at = (Get-Date).ToString('o')
  project_root = $ProjectRoot
  project_root_hash_anchor = (Get-FileHash -LiteralPath (Join-Path $ProjectRoot 'backend/src/palwakf_local_agents/app.py') -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash
  known_workspace_static_root = $knownWorkspaceStatic
  known_workspace_static_state = $knownWorkspaceStaticState
  static_frontend_mode = $staticMode
  framework_mode = $frameworkMode
  static_roots = @($staticRoots | ForEach-Object { $_.FullName.Substring($ProjectRoot.Length).TrimStart('\\') })
  assets = @($assetRows)
  route_inventory = @($routeRows | Sort-Object route, method, file)
  frontend_framework_inventory = @($frameworkRows)
  fetch_inventory = @($fetchRows)
  execution_boundaries = [pscustomobject]@{
    project_mutation = 'NONE'
    model_execution = 'NONE'
    pilot_execution = 'NOT_EXECUTED'
    service_start = 'NONE'
    git_write = 'NONE'
    external_network = 'NONE'
  }
}

$jsonPath = Join-Path $evidenceRoot 'frontend_baseline.json'
$mdPath = Join-Path $evidenceRoot 'frontend_baseline.md'
$zipPath = "$evidenceRoot.zip"
$baseline | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
[void]$md.Add('# Local Agents Multi-Workspace Operations Frontend V1 Baseline')
[void]$md.Add('')
[void]$md.Add(('- Generated at: {0}' -f $baseline.generated_at))
[void]$md.Add(('- Static frontend mode: {0}' -f $staticMode))
[void]$md.Add(('- Framework mode: {0}' -f $frameworkMode))
[void]$md.Add(('- Known workspace static root: {0}' -f $knownWorkspaceStaticState))
[void]$md.Add(('- Static roots: {0}' -f $staticRoots.Count))
[void]$md.Add(('- Static assets: {0}' -f $assetRows.Count))
[void]$md.Add(('- API routes discovered: {0}' -f $routeRows.Count))
[void]$md.Add(('- Fetch calls discovered: {0}' -f $fetchRows.Count))
[void]$md.Add(('- Framework config files: {0}' -f $frameworkRows.Count))
[void]$md.Add('')
[void]$md.Add('## Boundary')
[void]$md.Add('- Project mutation: NONE')
[void]$md.Add('- Model execution: NONE')
[void]$md.Add('- Pilot execution: NOT_EXECUTED')
[void]$md.Add('- Service start: NONE')
[void]$md.Add('- External network: NONE')
$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path "$evidenceRoot/*" -DestinationPath $zipPath -Force

'===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 BASELINE ====='
('KNOWN_WORKSPACE_STATIC_ROOT_STATE={0}' -f $knownWorkspaceStaticState)
('STATIC_FRONTEND_MODE={0}' -f $staticMode)
('FRAMEWORK_MODE={0}' -f $frameworkMode)
('STATIC_ROOT_COUNT={0}' -f $staticRoots.Count)
('STATIC_ASSET_COUNT={0}' -f $assetRows.Count)
('ROUTE_INVENTORY_COUNT={0}' -f $routeRows.Count)
('FETCH_INVENTORY_COUNT={0}' -f $fetchRows.Count)
('FRONTEND_FRAMEWORK_CONFIG_COUNT={0}' -f $frameworkRows.Count)
('BASELINE_MANIFEST={0}' -f $jsonPath)
('BASELINE_REPORT_MARKDOWN={0}' -f $mdPath)
('EVIDENCE_ARCHIVE={0}' -f $zipPath)
'PROJECT_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SERVICE_START=NONE'
'GIT_WRITE=NONE'
'EXTERNAL_NETWORK=NONE'
'BASELINE_RESULT=PASS'
