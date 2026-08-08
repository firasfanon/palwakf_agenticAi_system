param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = 'Stop'

$baselineScript = Join-Path $PackageRoot 'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaseline.ps1'
$whatIfScript = Join-Path $PackageRoot 'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineWhatIf.ps1'
foreach ($requiredPath in @($baselineScript, $whatIfScript)) {
  if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
    throw ('RUNTIME_SELF_TEST_DEPENDENCY_MISSING={0}' -f $requiredPath)
  }
}

$fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('local_agents_frontend_v1_runtime_fixture_{0}' -f ([Guid]::NewGuid().ToString('N')))
$fixtureProject = Join-Path $fixtureRoot 'project'
$fixtureStatic = Join-Path $fixtureProject 'backend/src/palwakf_local_agents/workspace_core/static'
$fixtureApp = Join-Path $fixtureProject 'backend/src/palwakf_local_agents/app.py'
$fixtureOutput = Join-Path $fixtureRoot 'baseline_output'

try {
  New-Item -ItemType Directory -Path $fixtureStatic -Force | Out-Null
  New-Item -ItemType Directory -Path (Split-Path -Parent $fixtureApp) -Force | Out-Null

  Set-Content -LiteralPath $fixtureApp -Value @(
    'from fastapi import FastAPI',
    'app = FastAPI()',
    '@app.get("/fixture")',
    'def fixture():',
    '    return {"ok": True}'
  ) -Encoding UTF8 -ErrorAction Stop

  Set-Content -LiteralPath (Join-Path $fixtureStatic 'index.html') -Value '<!doctype html><html><body>fixture</body></html>' -Encoding UTF8 -ErrorAction Stop
  Set-Content -LiteralPath (Join-Path $fixtureStatic 'app.js') -Value 'fetch("/fixture");' -Encoding UTF8 -ErrorAction Stop
  Set-Content -LiteralPath (Join-Path $fixtureStatic 'styles.css') -Value 'body { margin: 0; }' -Encoding UTF8 -ErrorAction Stop

  $baselineOutput = @(& $baselineScript -PackageRoot $PackageRoot -ProjectRoot $fixtureProject -OutputRoot $fixtureOutput)
  $baselineManifestLine = $null
  foreach ($line in $baselineOutput) {
    if (($line -is [string]) -and $line.StartsWith('BASELINE_MANIFEST=')) {
      $baselineManifestLine = $line
    }
  }
  if ([string]::IsNullOrWhiteSpace($baselineManifestLine)) {
    throw 'RUNTIME_SELF_TEST_BASELINE_MANIFEST_NOT_EMITTED'
  }

  $baselineManifest = $baselineManifestLine.Substring('BASELINE_MANIFEST='.Length)
  if (-not (Test-Path -LiteralPath $baselineManifest -PathType Leaf)) {
    throw 'RUNTIME_SELF_TEST_BASELINE_MANIFEST_NOT_CREATED'
  }

  $document = Get-Content -LiteralPath $baselineManifest -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
  if ($document.contract -ne 'LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_FINAL_BASELINE') {
    throw 'RUNTIME_SELF_TEST_BASELINE_CONTRACT_INVALID'
  }
  if (@($document.static_roots).Count -ne 1) {
    throw 'RUNTIME_SELF_TEST_STATIC_ROOT_COUNT_UNEXPECTED'
  }
  if (@($document.assets).Count -lt 3) {
    throw 'RUNTIME_SELF_TEST_ASSET_SERIALIZATION_FAILED'
  }
  # The first asset append receives an empty ArrayList. A successful baseline
  # here proves the repaired empty-collection binding path at runtime.
  if (@($document.assets).Count -ne 3) {
    throw 'RUNTIME_SELF_TEST_EMPTY_COLLECTION_FIRST_APPEND_FAILED'
  }
  if (@($document.route_inventory).Count -lt 1) {
    throw 'RUNTIME_SELF_TEST_ROUTE_SERIALIZATION_FAILED'
  }
  if (@($document.fetch_inventory).Count -lt 1) {
    throw 'RUNTIME_SELF_TEST_FETCH_SERIALIZATION_FAILED'
  }

  $whatIfOutput = @(& $whatIfScript -PackageRoot $PackageRoot -ProjectRoot $fixtureProject -BaselineManifest $baselineManifest)
  $whatIfPass = $false
  foreach ($line in $whatIfOutput) {
    if (($line -is [string]) -and ($line -eq 'WHATIF_STATUS=COMPLETE')) {
      $whatIfPass = $true
    }
  }
  if (-not $whatIfPass) {
    throw 'RUNTIME_SELF_TEST_WHATIF_FAILED'
  }

  '===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 FINAL BASELINE CARRIER RUNTIME SELF-TEST ====='
  'RUNTIME_FIXTURE_CREATION=PASS'
  'RUNTIME_EMPTY_COLLECTION_FIRST_APPEND=PASS'
  'RUNTIME_BASELINE_JSON_SERIALIZATION=PASS'
  'RUNTIME_MANIFEST_GENERATION=PASS'
  'RUNTIME_WHATIF_BINDING=PASS'
  'RUNTIME_FIXTURE_SELF_TEST=PASS'
  'PROJECT_MUTATION=NONE'
  'MODEL_EXECUTION=NONE'
  'PILOT_EXECUTION=NOT_EXECUTED'
  'SERVICE_START=NONE'
  'SHELL_EXECUTION=NONE'
  'GIT_WRITE=NONE'
  'EXTERNAL_NETWORK=NONE'
}
finally {
  Remove-Item -LiteralPath $fixtureRoot -Recurse -Force -ErrorAction SilentlyContinue
}
