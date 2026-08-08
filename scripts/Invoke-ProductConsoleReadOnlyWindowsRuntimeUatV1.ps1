[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$WorktreePath,
  [Parameter(Mandatory = $true)][string]$CandidateRoot,
  [Parameter(Mandatory = $true)][string]$BackendStartCommand,
  [Parameter(Mandatory = $true)][string]$OutputDirectory,
  [string]$BaseUrl = 'http://127.0.0.1:8787',
  [string]$NodePath = 'node.exe',
  [string]$EdgePath = 'msedge.exe',
  [int]$HealthTimeoutSeconds = 45,
  [switch]$KeepBackendForForensics
)
$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Code) { if (-not $Condition) { throw $Code } }
function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Write-Json([string]$Path, $Value) { $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding UTF8 }
function Test-Health([string]$Url) {
  try {
    $response = Invoke-WebRequest -Uri "$Url/health" -Method GET -UseBasicParsing -TimeoutSec 5
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
  } catch { return $false }
}

$WorktreePath = (Resolve-Path -LiteralPath $WorktreePath).Path
$CandidateRoot = (Resolve-Path -LiteralPath $CandidateRoot).Path
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
$startTime = Get-Date
$backend = $null
$status = [ordered]@{
  authorization = 'AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_RUNTIME_UAT_V1_ISOLATED_WORKTREE_ONLY'
  execution_scope = 'ISOLATED_WORKTREE_ONLY'
  source_project_mutation = 'NONE'
  sqlite_migration = 'NOT_EXECUTED'
  model_execution = 'NOT_EXECUTED'
  pilot_execution = 'NOT_EXECUTED'
  production = 'NOT_APPROVED'
  runtime_uat = 'STARTED'
  harness_reconciliation = 'POSTIMAGE_VALIDATION_REQUIRED'
}

try {
  Require (Test-Path -LiteralPath (Join-Path $WorktreePath '.git')) 'ISOLATED_GIT_WORKTREE_REQUIRED'
  Require (Test-Path -LiteralPath (Join-Path $WorktreePath 'frontend/package.json')) 'FRONTEND_PACKAGE_JSON_REQUIRED'
  Require (Test-Path -LiteralPath (Join-Path $CandidateRoot 'POSTIMAGE_SHA256.json')) 'POSTIMAGE_CONTRACT_REQUIRED'
  Require (Test-Path -LiteralPath (Join-Path $CandidateRoot 'PATCH_MANIFEST.json')) 'PATCH_MANIFEST_REQUIRED'
  Require (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'run_read_only_browser_uat.mjs')) 'BROWSER_UAT_SCRIPT_REQUIRED'

  # UAT validates the already-applied postimage. It intentionally does NOT rerun
  # the prior preimage gate, because that gate belongs before the payload copy.
  $postimage = Get-Content -LiteralPath (Join-Path $CandidateRoot 'POSTIMAGE_SHA256.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($property in $postimage.PSObject.Properties) {
    $target = Join-Path $WorktreePath $property.Name
    Require (Test-Path -LiteralPath $target) "POSTIMAGE_MISSING=$($property.Name)"
    Require ((Get-Sha256 $target) -eq $property.Value) "POSTIMAGE_HASH_MISMATCH=$($property.Name)"
  }
  $status.postimage_validation = 'PASS'

  $manifest = Get-Content -LiteralPath (Join-Path $CandidateRoot 'PATCH_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  $approved = @($manifest.files | ForEach-Object { $_.path })
  Require ($approved.Count -eq 7) 'APPROVED_SOURCE_FILE_COUNT_MUST_EQUAL_7'
  $changed = @(git -C $WorktreePath diff --name-only HEAD -- frontend/src)
  $unapproved = @($changed | Where-Object { $_ -notin $approved })
  Require ($unapproved.Count -eq 0) ("UNAPPROVED_FRONTEND_SOURCE_CHANGE=" + ($unapproved -join ','))
  $status.approved_source_change_count = $changed.Count
  $status.unapproved_source_change_count = $unapproved.Count
  $status.source_scope = 'PASS'

  # Explicitly block a migration/seed command in this UAT runner.
  $forbiddenBackendCommand = '(?i)(alembic\s+(upgrade|downgrade)|\bmigrate\b|makemigrations|\bseed\b|init[-_ ]?db|create[-_ ]?tables?)'
  Require ($BackendStartCommand -notmatch $forbiddenBackendCommand) 'BACKEND_COMMAND_CONTAINS_MIGRATION_OR_SEED_OPERATION'
  $status.backend_command_gate = 'PASS'

  Push-Location (Join-Path $WorktreePath 'frontend')
  try {
    & npm ci --ignore-scripts --offline | Tee-Object -FilePath (Join-Path $OutputDirectory 'NPM_CI_OFFLINE.log')
    Require ($LASTEXITCODE -eq 0) 'NPM_CI_OFFLINE_FAILED'
    & npm run check | Tee-Object -FilePath (Join-Path $OutputDirectory 'TSC_NO_EMIT.log')
    Require ($LASTEXITCODE -eq 0) 'TSC_NO_EMIT_FAILED'
    & npm run build | Tee-Object -FilePath (Join-Path $OutputDirectory 'VITE_BUILD.log')
    Require ($LASTEXITCODE -eq 0) 'VITE_BUILD_FAILED'
  } finally { Pop-Location }
  $status.npm_ci_offline = 'PASS'; $status.tsc_no_emit = 'PASS'; $status.vite_build = 'PASS'

  $backendStdOut = Join-Path $OutputDirectory 'BACKEND_STDOUT.log'
  $backendStdErr = Join-Path $OutputDirectory 'BACKEND_STDERR.log'
  $backend = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d','/s','/c',$BackendStartCommand) -WorkingDirectory $WorktreePath -RedirectStandardOutput $backendStdOut -RedirectStandardError $backendStdErr -PassThru -WindowStyle Hidden
  $status.backend_pid = $backend.Id
  $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
  while ((Get-Date) -lt $deadline -and -not (Test-Health $BaseUrl)) {
    if ($backend.HasExited) { throw "BACKEND_EXITED_EARLY=$($backend.ExitCode)" }
    Start-Sleep -Milliseconds 500
  }
  Require (Test-Health $BaseUrl) 'HEALTH_ENDPOINT_NOT_READY'
  $status.health_get = 'PASS'

  $nodeScript = Join-Path $PSScriptRoot 'run_read_only_browser_uat.mjs'
  & $NodePath $nodeScript --base-url $BaseUrl --output (Join-Path $OutputDirectory 'BROWSER') --edge-path $EdgePath 2>&1 | Tee-Object -FilePath (Join-Path $OutputDirectory 'BROWSER_UAT.log')
  Require ($LASTEXITCODE -eq 0) "BROWSER_RUNTIME_UAT_FAILED_EXIT=$LASTEXITCODE"
  $browserReportPath = Join-Path $OutputDirectory 'BROWSER/BROWSER_UAT_REPORT.json'
  Require (Test-Path -LiteralPath $browserReportPath) 'BROWSER_UAT_REPORT_MISSING'
  $browserReport = Get-Content -LiteralPath $browserReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
  Require ($browserReport.result -eq 'WINDOWS_RUNTIME_UAT_PASS') "BROWSER_UAT_RESULT=$($browserReport.result)"
  $status.runtime_uat = 'PASS'
  $status.browser_result = $browserReport.result
  $status.baseline_acceptance = 'READY_FOR_HUMAN_EVIDENCE_REVIEW'
  $status.result = 'WINDOWS_RUNTIME_UAT_PASS__BASELINE_ACCEPTANCE_REQUIRES_EVIDENCE_REVIEW'
} catch {
  $status.runtime_uat = 'FAIL'
  $status.result = 'WINDOWS_RUNTIME_UAT_FAIL_OR_HARNESS_ERROR'
  $status.error = $_.Exception.Message
  throw
} finally {
  $status.completed_utc = (Get-Date).ToUniversalTime().ToString('o')
  $status.duration_seconds = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 3)
  Write-Json (Join-Path $OutputDirectory 'UAT_EXECUTION_STATUS.json') $status
  if ($backend -and -not $KeepBackendForForensics) {
    try { if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force } } catch {}
  }
}
