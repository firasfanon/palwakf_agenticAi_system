# UTF-8 with BOM. Compatible with Windows PowerShell 5.1 and PowerShell 7+.
# V8 worktree cleanup repair: terminates only Edge/Chrome processes bound to the isolated per-run browser profiles before deletion; cleanup retries are explicit and evidence-backed.
[CmdletBinding()]
param(
  [string]$ProjectRoot = '',
  [ValidateSet('OfflineCache', 'Registry')]
  [string]$DependencyMode = 'OfflineCache',
  [int]$Port = 8877,
  [string]$PythonExe,
  [string]$BrowserPath,
  [switch]$SkipVisibleBrowser,
  [switch]$SkipHeadlessCapture,
  [switch]$NonInteractive,
  [switch]$RetainWorktree
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 evaluates param defaults before $PSScriptRoot is reliably populated.
# Resolve the project root after script invocation context is available.
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $scriptPathForRoot = $PSCommandPath
  if ([string]::IsNullOrWhiteSpace($scriptPathForRoot)) { $scriptPathForRoot = $MyInvocation.MyCommand.Path }
  if ([string]::IsNullOrWhiteSpace($scriptPathForRoot)) { throw 'PROJECT_ROOT_REQUIRED__PASS_PROJECTROOT_OR_RUN_WITH_POWERSHELL_FILE_MODE.' }
  $scriptDirectoryForRoot = Split-Path -Parent $scriptPathForRoot
  $ProjectRoot = Split-Path -Parent $scriptDirectoryForRoot
}

function Write-UatLog {
  param([Parameter(Mandatory = $true)][string]$Message)
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
  Write-Host $line
  if ($script:RunLogPath) {
    Add-Content -LiteralPath $script:RunLogPath -Value $line -Encoding UTF8
  }
}

function Write-JsonFile {
  param(
    [Parameter(Mandatory = $true)][object]$Value,
    [Parameter(Mandatory = $true)][string]$Path
  )
  $Value | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-Sha256Map {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string[]]$RelativePaths
  )
  $result = [ordered]@{}
  foreach ($relative in $RelativePaths) {
    $fullPath = Join-Path $Root $relative
    if (-not (Test-Path -LiteralPath $fullPath)) {
      throw "MISSING_BASELINE_FILE: $relative"
    }
    $result[$relative] = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash
  }
  return $result
}

function Get-ExternalText {
  param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  $rawOutput = @()
  try {
    $rawOutput = @(& $Executable @Arguments 2>&1)
  }
  catch {
    throw "EXTERNAL_PROBE_START_FAILED: $Executable :: $($_.Exception.Message)"
  }

  $exitCode = $LASTEXITCODE
  if ($null -eq $exitCode) { $exitCode = 0 }
  $parts = @(
    foreach ($entry in @($rawOutput)) {
      if ($null -ne $entry) { [string]$entry }
    }
  )
  $textValue = (($parts -join [Environment]::NewLine).Trim())
  return [pscustomobject]@{
    executable = $Executable
    arguments = $Arguments
    exit_code = [int]$exitCode
    text = $textValue
  }
}

function Resolve-Python {
  param([string]$Root, [string]$RequestedPath)
  $candidates = @()
  if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) { $candidates += $RequestedPath }
  $venvPython = Join-Path $Root '.venv\Scripts\python.exe'
  if (Test-Path -LiteralPath $venvPython) { $candidates += $venvPython }
  $command = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace([string]$command.Source)) { $candidates += $command.Source }

  $diagnostics = @()
  foreach ($candidate in @($candidates | Select-Object -Unique)) {
    if ([string]::IsNullOrWhiteSpace([string]$candidate)) { continue }
    if (-not (Test-Path -LiteralPath $candidate)) {
      $diagnostics += "missing=$candidate"
      continue
    }
    $probe = Get-ExternalText -Executable $candidate -Arguments @('-c', "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    $diagnostics += "path=$candidate;exit=$($probe.exit_code);output=$($probe.text)"
    if ($probe.exit_code -eq 0 -and $probe.text -match '^3\.(11|12)\.\d+$') {
      return [pscustomobject]@{ path = $candidate; version = $probe.text }
    }
  }

  $detail = if ($diagnostics.Length -gt 0) { $diagnostics -join ' | ' } else { 'no python.exe candidate was discovered' }
  throw "PYTHON_3_11_OR_3_12_WITH_FASTAPI_AND_UVICORN_REQUIRED. Probes: $detail"
}

function Resolve-Browser {
  param([string]$RequestedPath)
  if ($RequestedPath) {
    if (-not (Test-Path -LiteralPath $RequestedPath)) { throw "BROWSER_NOT_FOUND: $RequestedPath" }
    return $RequestedPath
  }

  $programFiles = [Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFiles)
  $programFilesX86 = [Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFilesX86)
  $localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
  $candidates = @(
    (Join-Path $programFilesX86 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $programFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $localAppData 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $programFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $programFilesX86 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $localAppData 'Google\Chrome\Application\chrome.exe')
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) { return $candidate }
  }
  throw 'EDGE_OR_CHROME_REQUIRED_FOR_LOCAL_BROWSER_UAT.'
}

function Resolve-NpmCmd {
  $candidates = @()
  $command = Get-Command 'npm.cmd' -CommandType Application -ErrorAction SilentlyContinue
  if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace([string]$command.Source)) {
    $candidates += [string]$command.Source
  }
  if (-not [string]::IsNullOrWhiteSpace([string]$env:ProgramFiles)) {
    $candidates += (Join-Path $env:ProgramFiles 'nodejs\npm.cmd')
  }
  if (-not [string]::IsNullOrWhiteSpace([string]${env:ProgramFiles(x86)})) {
    $candidates += (Join-Path ${env:ProgramFiles(x86)} 'nodejs\npm.cmd')
  }

  foreach ($candidate in @($candidates | Select-Object -Unique)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$candidate) -and (Test-Path -LiteralPath $candidate)) {
      return [System.IO.Path]::GetFullPath([string]$candidate)
    }
  }
  throw 'NPM_CMD_REQUIRED_FOR_WINDOWS_NPM_EXECUTION.'
}

function ConvertTo-ProcessArgument {
  param([Parameter(Mandatory = $true)][string]$Value)
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '"', '\"') + '"'
}

function Invoke-DirectProcessLogged {
  param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$LogPath,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory
  )

  if (-not (Test-Path -LiteralPath $Executable)) { throw "EXECUTABLE_NOT_FOUND: $Executable" }
  if (-not (Test-Path -LiteralPath $WorkingDirectory)) { throw "WORKING_DIRECTORY_NOT_FOUND: $WorkingDirectory" }

  $quotedArguments = @(
    foreach ($argument in $Arguments) {
      ConvertTo-ProcessArgument -Value ([string]$argument)
    }
  )
  $argumentText = $quotedArguments -join ' '
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.WorkingDirectory = $WorkingDirectory
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true

  $extension = [System.IO.Path]::GetExtension($Executable)
  if ($extension -match '^(?i:\.(cmd|bat))$') {
    $commandText = ('"{0}" {1}' -f $Executable, $argumentText).Trim()
    $psi.FileName = $env:ComSpec
    $psi.Arguments = ('/d /s /c "{0}"' -f $commandText)
  }
  else {
    $commandText = ('"{0}" {1}' -f $Executable, $argumentText).Trim()
    $psi.FileName = $Executable
    $psi.Arguments = $argumentText
  }

  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $psi
  if (-not $process.Start()) { throw "EXTERNAL_COMMAND_START_FAILED: $commandText" }
  $stdout = $process.StandardOutput.ReadToEnd()
  $stderr = $process.StandardError.ReadToEnd()
  $process.WaitForExit()
  $exitCode = [int]$process.ExitCode
  $logLines = @(
    ("COMMAND={0}" -f $commandText),
    ("EXIT_CODE={0}" -f $exitCode),
    '--- STDOUT ---',
    $stdout,
    '--- STDERR ---',
    $stderr,
    ''
  )
  Add-Content -LiteralPath $LogPath -Value ($logLines -join [Environment]::NewLine) -Encoding UTF8
  return [pscustomobject]@{
    command = $commandText
    exit_code = $exitCode
    stdout = $stdout
    stderr = $stderr
  }
}

function Invoke-ExternalLogged {
  param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$LogPath,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory
  )

  # npm.ps1 can transform ordinary npm stderr notices into PowerShell error records under ErrorActionPreference=Stop.
  # Direct process capture keeps stderr as evidence; the native Exit Code remains the only success authority.
  $result = Invoke-DirectProcessLogged -Executable $Executable -Arguments $Arguments -LogPath $LogPath -WorkingDirectory $WorkingDirectory
  if ($result.exit_code -ne 0) {
    throw "EXTERNAL_COMMAND_FAILED: $($result.command) EXIT=$($result.exit_code) LOG=$LogPath"
  }
  return $result
}

function Invoke-HttpEvidence {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [string]$Method = 'GET'
  )
  $started = Get-Date
  $result = [ordered]@{
    uri = $Uri
    method = $Method
    status = $null
    elapsed_ms = $null
    content_type = $null
    set_cookie_present = $false
    error = $null
  }
  try {
    $response = Invoke-WebRequest -Uri $Uri -Method $Method -UseBasicParsing -TimeoutSec 20 -ErrorAction Stop
    $result.status = [int]$response.StatusCode
    $result.content_type = $response.Headers['Content-Type']
    $result.set_cookie_present = [bool]$response.Headers['Set-Cookie']
  }
  catch {
    $webResponse = $_.Exception.Response
    if ($null -ne $webResponse) {
      $result.status = [int]$webResponse.StatusCode
      $result.content_type = $webResponse.ContentType
      $result.set_cookie_present = [bool]$webResponse.Headers['Set-Cookie']
    }
    else {
      $result.error = $_.Exception.Message
    }
  }
  $result.elapsed_ms = [int]((Get-Date) - $started).TotalMilliseconds
  return [pscustomobject]$result
}

function Wait-ForHealth {
  param([Parameter(Mandatory = $true)][string]$BaseUrl)
  for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
      $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
      if ($health.safety_ok -eq $true -and $health.agent_execution_enabled -eq $false -and $health.platform_mutation_enabled -eq $false -and $health.database_access_enabled -eq $false) {
        return $health
      }
    }
    catch {
      Start-Sleep -Seconds 1
    }
  }
  throw 'LOCAL_RUNTIME_HEALTH_OR_SAFETY_GATE_FAILED.'
}

function Invoke-HeadlessBrowserCapture {
  param(
    [Parameter(Mandatory = $true)][string]$Browser,
    [Parameter(Mandatory = $true)][string]$ProfileDirectory,
    [Parameter(Mandatory = $true)][string]$Uri,
    [Parameter(Mandatory = $true)][string]$PngPath,
    [Parameter(Mandatory = $true)][string]$DomPath,
    [Parameter(Mandatory = $true)][string]$LogPath
  )
  $arguments = @(
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--force-color-profile=srgb',
    '--window-size=1440,1200',
    '--virtual-time-budget=5000',
    "--user-data-dir=$ProfileDirectory",
    "--screenshot=$PngPath",
    $Uri
  )
  $screenshotResult = Invoke-DirectProcessLogged -Executable $Browser -Arguments $arguments -LogPath $LogPath -WorkingDirectory (Split-Path -Parent $ProfileDirectory)
  if ($screenshotResult.exit_code -ne 0 -or -not (Test-Path -LiteralPath $PngPath)) {
    throw "HEADLESS_SCREENSHOT_FAILED: $Uri EXIT=$($screenshotResult.exit_code) LOG=$LogPath"
  }

  $domArguments = @(
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--virtual-time-budget=5000',
    "--user-data-dir=$ProfileDirectory",
    '--dump-dom',
    $Uri
  )
  $domResult = Invoke-DirectProcessLogged -Executable $Browser -Arguments $domArguments -LogPath $LogPath -WorkingDirectory (Split-Path -Parent $ProfileDirectory)
  Set-Content -LiteralPath $DomPath -Value $domResult.stdout -Encoding UTF8
  if ($domResult.exit_code -ne 0 -or -not (Test-Path -LiteralPath $DomPath)) {
    throw "HEADLESS_DOM_CAPTURE_FAILED: $Uri EXIT=$($domResult.exit_code) LOG=$LogPath"
  }
}

function Read-HarSummary {
  param([Parameter(Mandatory = $true)][string]$HarPath)
  if (-not (Test-Path -LiteralPath $HarPath)) {
    return [pscustomobject]@{
      captured = $false
      entry_count = 0
      non_read_method_count = $null
      authorization_header_count = $null
      set_cookie_response_count = $null
      result = 'NOT_CAPTURED'
    }
  }

  try {
    $har = Get-Content -LiteralPath $HarPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $entries = @($har.log.entries)
    $nonReadMethods = @($entries | Where-Object { $_.request.method -notin @('GET', 'HEAD', 'OPTIONS') })
    $authorizationHeaders = @(
      foreach ($entry in $entries) {
        foreach ($header in @($entry.request.headers)) {
          if ($header.name -match '^(?i:authorization)$') { $header }
        }
      }
    )
    $setCookieHeaders = @(
      foreach ($entry in $entries) {
        foreach ($header in @($entry.response.headers)) {
          if ($header.name -match '^(?i:set-cookie)$') { $header }
        }
      }
    )
    $result = if ($nonReadMethods.Count -eq 0 -and $authorizationHeaders.Count -eq 0 -and $setCookieHeaders.Count -eq 0) { 'PASS' } else { 'FAIL' }
    return [pscustomobject]@{
      captured = $true
      entry_count = $entries.Count
      non_read_method_count = $nonReadMethods.Count
      authorization_header_count = $authorizationHeaders.Count
      set_cookie_response_count = $setCookieHeaders.Count
      result = $result
    }
  }
  catch {
    return [pscustomobject]@{
      captured = $true
      entry_count = $null
      non_read_method_count = $null
      authorization_header_count = $null
      set_cookie_response_count = $null
      result = "INVALID_HAR: $($_.Exception.Message)"
    }
  }
}


function Resolve-HarEvidence {
  param(
    [Parameter(Mandatory = $true)][string]$EvidenceRoot,
    [Parameter(Mandatory = $true)][string]$CanonicalHarPath
  )

  $canonicalLeaf = Split-Path -Leaf $CanonicalHarPath
  $candidates = @(
    Get-ChildItem -LiteralPath $EvidenceRoot -File -Filter '*.har' -ErrorAction Stop |
      Sort-Object -Property Name
  )
  $candidateLeaves = @($candidates | ForEach-Object { $_.Name })
  $canonicalExists = Test-Path -LiteralPath $CanonicalHarPath

  if ($canonicalExists) {
    return [pscustomobject]@{
      result = 'CANONICAL_EXACT'
      expected_filename = $canonicalLeaf
      selected_filename = $canonicalLeaf
      selected_path = $CanonicalHarPath
      candidate_count = @($candidates).Count
      candidate_filenames = @($candidateLeaves)
      reconciliation_applied = $false
      error = $null
    }
  }

  if (@($candidates).Count -eq 0) {
    return [pscustomobject]@{
      result = 'NOT_FOUND'
      expected_filename = $canonicalLeaf
      selected_filename = $null
      selected_path = $null
      candidate_count = 0
      candidate_filenames = @()
      reconciliation_applied = $false
      error = $null
    }
  }

  if (@($candidates).Count -gt 1) {
    return [pscustomobject]@{
      result = 'AMBIGUOUS'
      expected_filename = $canonicalLeaf
      selected_filename = $null
      selected_path = $null
      candidate_count = @($candidates).Count
      candidate_filenames = @($candidateLeaves)
      reconciliation_applied = $false
      error = 'MULTIPLE_HAR_FILES_REQUIRE_OPERATOR_SELECTION'
    }
  }

  $sourceHarPath = [string]$candidates[0].FullName
  $temporaryCanonicalPath = "$CanonicalHarPath.reconciliation.tmp"
  if (Test-Path -LiteralPath $temporaryCanonicalPath) {
    Remove-Item -LiteralPath $temporaryCanonicalPath -Force -ErrorAction Stop
  }

  try {
    [System.IO.File]::Copy($sourceHarPath, $temporaryCanonicalPath, $true)
    Move-Item -LiteralPath $temporaryCanonicalPath -Destination $CanonicalHarPath -ErrorAction Stop
  }
  catch {
    if (Test-Path -LiteralPath $temporaryCanonicalPath) {
      Remove-Item -LiteralPath $temporaryCanonicalPath -Force -ErrorAction SilentlyContinue
    }
    throw "HAR_FILENAME_RECONCILIATION_COPY_FAILED: source=$sourceHarPath target=$CanonicalHarPath error=$($_.Exception.Message)"
  }

  return [pscustomobject]@{
    result = 'RECONCILED_SINGLE_CANDIDATE'
    expected_filename = $canonicalLeaf
    selected_filename = [string]$candidates[0].Name
    selected_path = $CanonicalHarPath
    candidate_count = 1
    candidate_filenames = @($candidateLeaves)
    reconciliation_applied = $true
    error = $null
  }
}

function Stop-IsolatedBrowserProfileProcesses {
  param(
    [Parameter(Mandatory = $true)][string]$BrowserExecutable,
    [Parameter(Mandatory = $true)][string]$ProfileDirectory,
    [Parameter(Mandatory = $true)][string]$Label
  )

  $profileFullPath = [System.IO.Path]::GetFullPath($ProfileDirectory)
  $processName = [System.IO.Path]::GetFileName($BrowserExecutable)
  $stopped = @()
  $errors = @()
  $matched = @()

  try {
    $candidates = @(
      Get-CimInstance Win32_Process -Filter ("Name = '{0}'" -f $processName) -ErrorAction Stop |
        Where-Object {
          $commandLine = [string]$_.CommandLine
          -not [string]::IsNullOrWhiteSpace($commandLine) -and
            $commandLine.IndexOf($profileFullPath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        }
    )
  }
  catch {
    $candidates = @()
    $errors += ("PROCESS_DISCOVERY_FAILED: {0}" -f $_.Exception.Message)
  }

  foreach ($candidate in $candidates) {
    $processId = [int]$candidate.ProcessId
    $matched += $processId
    try {
      Stop-Process -Id $processId -Force -ErrorAction Stop
      $stopped += $processId
    }
    catch {
      $errors += ("PROCESS_STOP_FAILED[{0}]: {1}" -f $processId, $_.Exception.Message)
    }
  }

  Start-Sleep -Milliseconds 750
  return [pscustomobject]@{
    label = $Label
    browser = $BrowserExecutable
    profile_directory = $profileFullPath
    matched_process_ids = @($matched)
    stopped_process_ids = @($stopped)
    errors = @($errors)
  }
}

function Remove-IsolatedWorktreeWithRetries {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$LogRoot,
    [int]$MaxAttempts = 5
  )

  $attempts = @()
  for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    try {
      if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
      }
      $attempts += [pscustomobject]@{ attempt = $attempt; result = 'PASS'; error = $null }
      return [pscustomobject]@{ result = 'PASS'; attempts = @($attempts) }
    }
    catch {
      $attempts += [pscustomobject]@{ attempt = $attempt; result = 'LOCK_OR_DELETE_FAILURE'; error = $_.Exception.Message }
      if ($attempt -lt $MaxAttempts) { Start-Sleep -Seconds 2 }
    }
  }

  $cleanupPath = Join-Path $LogRoot 'worktree_cleanup_attempts.json'
  Write-JsonFile -Value ([pscustomobject]@{ result = 'FAIL'; worktree = $Path; attempts = @($attempts) }) -Path $cleanupPath
  $lastError = if ($attempts.Count -gt 0) { [string]$attempts[$attempts.Count - 1].error } else { 'UNKNOWN_CLEANUP_ERROR' }
  throw "WORKTREE_CLEANUP_FAILED_AFTER_PROFILE_PROCESS_TERMINATION: $lastError"
}

$originalEnvironment = @{}
$environmentKeys = @('LOCAL_AGENT_HOST', 'LOCAL_AGENT_PORT', 'ALLOW_AGENT_EXECUTION', 'ALLOW_PLATFORM_MUTATION', 'ALLOW_DATABASE_ACCESS', 'PYTHONPATH')
foreach ($key in $environmentKeys) { $originalEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
$serviceProcess = $null
$visibleBrowserProcess = $null
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$runId = "WINDOWS_LOCAL_BROWSER_UAT_$((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))"
$EvidenceRoot = Join-Path $Root ("output\windows_local_browser_uat\$runId")
$Worktree = Join-Path $EvidenceRoot 'worktree'
$CaptureRoot = Join-Path $EvidenceRoot 'browser_capture'
$LogRoot = Join-Path $EvidenceRoot 'logs'
$script:RunLogPath = $null
$script:CurrentStage = 'INITIALIZATION'

try {
  if ($env:OS -ne 'Windows_NT') { throw 'WINDOWS_ONLY_RUNNER. Execute this script on the authorized Windows local environment.' }
  if (-not (Test-Path -LiteralPath (Join-Path $Root 'frontend/package-lock.json'))) { throw 'PACKAGE_LOCK_MISSING.' }
  if (-not (Test-Path -LiteralPath (Join-Path $Root 'backend/src/palwakf_local_agents/app.py'))) { throw 'BACKEND_APP_MISSING.' }
  if (Test-Path -LiteralPath $EvidenceRoot) { throw "EVIDENCE_ROOT_ALREADY_EXISTS: $EvidenceRoot" }

  New-Item -ItemType Directory -Path $EvidenceRoot, $CaptureRoot, $LogRoot -Force | Out-Null
  $script:RunLogPath = Join-Path $LogRoot 'runtime.log'
  Write-UatLog "RUN_ID=$runId"
  Write-UatLog "PROJECT_ROOT=$Root"
  Write-UatLog "DEPENDENCY_MODE=$DependencyMode"

  $script:CurrentStage = 'SOURCE_PREFLIGHT'
  $trackedFiles = @(
    'backend/src/palwakf_local_agents/app.py',
    'backend/src/palwakf_local_agents/settings.py',
    'backend/src/palwakf_local_agents/store.py',
    'frontend/package.json',
    'frontend/package-lock.json',
    'frontend/vite.config.ts',
    'frontend/src/api/client.ts'
  )
  $preimageHashes = Get-Sha256Map -Root $Root -RelativePaths $trackedFiles
  Write-JsonFile -Value $preimageHashes -Path (Join-Path $EvidenceRoot 'source_preimage_sha256.json')

  $script:CurrentStage = 'PYTHON_DISCOVERY'
  $python = Resolve-Python -Root $Root -RequestedPath $PythonExe
  Write-UatLog "PYTHON_SELECTED=$($python.path) VERSION=$($python.version)"

  $script:CurrentStage = 'BROWSER_DISCOVERY'
  $browser = Resolve-Browser -RequestedPath $BrowserPath
  $browserProbe = Get-ExternalText -Executable $browser -Arguments @('--version')
  if ($browserProbe.exit_code -ne 0) {
    throw "BROWSER_VERSION_PROBE_PROCESS_FAILED: path=$browser exit=$($browserProbe.exit_code) output=$($browserProbe.text)"
  }

  # Microsoft Edge may return exit code 0 but no stdout for --version in some managed Windows environments.
  # Treat process success + executable existence as the discovery gate; collect a file-version fallback for evidence.
  $browserVersion = [string]$browserProbe.text
  if ([string]::IsNullOrWhiteSpace($browserVersion)) {
    try {
      $browserFile = Get-Item -LiteralPath $browser -ErrorAction Stop
      $browserVersion = [string]$browserFile.VersionInfo.ProductVersion
      if ([string]::IsNullOrWhiteSpace($browserVersion)) {
        $browserVersion = [string]$browserFile.VersionInfo.FileVersion
      }
    }
    catch {
      $browserVersion = ''
    }
  }
  if ([string]::IsNullOrWhiteSpace($browserVersion)) {
    $browserVersion = 'UNREPORTED__VERSION_PROBE_EXIT_0'
  }
  Write-UatLog "BROWSER_SELECTED=$browser VERSION=$browserVersion VERSION_PROBE_EXIT=$($browserProbe.exit_code)"

  $script:CurrentStage = 'NODE_NPM_DISCOVERY'
  $nodeProbe = Get-ExternalText -Executable 'node' -Arguments @('--version')
  $npmExecutable = Resolve-NpmCmd
  $npmProbe = Get-ExternalText -Executable $npmExecutable -Arguments @('--version')
  $nodeVersion = $nodeProbe.text
  $npmVersion = $npmProbe.text
  if ($nodeProbe.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($nodeVersion) -or $npmProbe.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($npmVersion)) {
    throw "NODE_AND_NPM_REQUIRED_FOR_FRONTEND_BUILD. node_exit=$($nodeProbe.exit_code);node_output=$nodeVersion;npm_exit=$($npmProbe.exit_code);npm_output=$npmVersion;npm_executable=$npmExecutable"
  }
  Write-UatLog "NODE_VERSION=$nodeVersion NPM_VERSION=$npmVersion NPM_EXECUTABLE=$npmExecutable"
  $environmentEvidence = [ordered]@{
    run_id = $runId
    powershell = $PSVersionTable.PSVersion.ToString()
    python_path = $python.path
    python_version = $python.version
    node_version = $nodeVersion
    npm_version = $npmVersion
    browser_path = $browser
    browser_version = $browserVersion
    dependency_mode = $DependencyMode
    target_bind = "127.0.0.1:$Port"
    source_mutation_policy = 'ORIGINAL_SOURCE_CODE_UNCHANGED__EVIDENCE_OUTPUT_ONLY'
    runtime_safety = [ordered]@{
      allow_agent_execution = $false
      allow_platform_mutation = $false
      allow_database_access = $false
    }
  }
  Write-JsonFile -Value $environmentEvidence -Path (Join-Path $EvidenceRoot 'environment.json')

  $script:CurrentStage = 'COPY_ISOLATED_WORKTREE'
  Write-UatLog 'COPY_ISOLATED_WORKTREE=START'
  $robocopyLog = Join-Path $LogRoot 'robocopy.log'
  $excludeDirectories = @('.git', '.idea', '.venv', 'node_modules', '__pycache__', 'output')
  $robocopyArguments = @($Root, $Worktree, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/XD') + $excludeDirectories + @('/XF', '*.pyc', '*.pyo', '*.sqlite', '*.sqlite-wal', '*.sqlite-shm')
  & robocopy @robocopyArguments 2>&1 | Tee-Object -FilePath $robocopyLog
  if ($LASTEXITCODE -gt 7) { throw "ROBOCOPY_FAILED: EXIT=$LASTEXITCODE" }
  Write-UatLog 'COPY_ISOLATED_WORKTREE=PASS'

  $worktreeHashes = Get-Sha256Map -Root $Worktree -RelativePaths $trackedFiles
  foreach ($relative in $trackedFiles) {
    if ($preimageHashes[$relative] -ne $worktreeHashes[$relative]) { throw "WORKTREE_PREIMAGE_MISMATCH: $relative" }
  }

  $frontendRoot = Join-Path $Worktree 'frontend'
  $script:CurrentStage = 'NPM_CI'
  Write-UatLog 'NPM_CI=START'
  # Registry mode must use an explicit public registry and a per-run cache.
  # The cache is isolated under evidence output, preventing ambient global-cache state from changing UAT results.
  $npmCiArgs = @('ci', '--ignore-scripts', '--no-audit', '--no-fund')
  $npmRegistry = 'OFFLINE_CACHE'
  $npmCachePath = ''
  if ($DependencyMode -eq 'OfflineCache') {
    $npmCiArgs += '--offline'
  }
  else {
    $npmRegistry = 'https://registry.npmjs.org/'
    $npmCachePath = Join-Path $EvidenceRoot 'npm-registry-cache'
    New-Item -ItemType Directory -Path $npmCachePath -Force | Out-Null
    $npmCiArgs += @('--registry', $npmRegistry, '--cache', $npmCachePath)
  }
  Write-UatLog "NPM_REGISTRY=$npmRegistry"
  if (-not [string]::IsNullOrWhiteSpace($npmCachePath)) { Write-UatLog "NPM_CACHE=$npmCachePath" }
  Invoke-ExternalLogged -Executable $npmExecutable -Arguments $npmCiArgs -LogPath (Join-Path $LogRoot 'npm-ci.log') -WorkingDirectory $frontendRoot
  Write-UatLog 'NPM_CI=PASS'
  $script:CurrentStage = 'TYPESCRIPT_CHECK'
  Invoke-ExternalLogged -Executable $npmExecutable -Arguments @('run', 'check') -LogPath (Join-Path $LogRoot 'npm-check.log') -WorkingDirectory $frontendRoot
  Write-UatLog 'TYPESCRIPT_CHECK=PASS'
  $script:CurrentStage = 'VITE_BUILD'
  Invoke-ExternalLogged -Executable $npmExecutable -Arguments @('run', 'build') -LogPath (Join-Path $LogRoot 'npm-build.log') -WorkingDirectory $frontendRoot
  Write-UatLog 'VITE_BUILD=PASS'

  $distIndex = Join-Path $frontendRoot 'dist\index.html'
  if (-not (Test-Path -LiteralPath $distIndex)) { throw 'REAL_DIST_INDEX_MISSING_AFTER_BUILD.' }
  $assetFiles = @(Get-ChildItem -LiteralPath (Join-Path $frontendRoot 'dist\assets') -File -ErrorAction Stop)
  if ($assetFiles.Count -lt 2) { throw 'REAL_DIST_ASSET_SET_INCOMPLETE.' }

  $clientSource = Get-Content -LiteralPath (Join-Path $frontendRoot 'src\api\client.ts') -Raw -Encoding UTF8
  $frontendStaticContract = [ordered]@{
    credentials_omit = ($clientSource -match 'credentials:\s*"omit"')
    method_get = ($clientSource -match 'method:\s*"GET"')
    no_authorization_literal = (-not ($clientSource -match '(?i)authorization|bearer'))
    no_web_storage_literal = (-not ($clientSource -match '(?i)localStorage|sessionStorage'))
    no_write_method_literal = (-not ($clientSource -match 'method:\s*"(POST|PUT|PATCH|DELETE)"'))
  }
  if ($frontendStaticContract.Values -contains $false) { throw 'REACT_READ_ONLY_STATIC_CONTRACT_FAILED.' }
  Write-JsonFile -Value $frontendStaticContract -Path (Join-Path $EvidenceRoot 'react_read_only_static_contract.json')

  $script:CurrentStage = 'REACT_STATIC_CONTRACT'
  $env:LOCAL_AGENT_HOST = '127.0.0.1'
  $env:LOCAL_AGENT_PORT = "$Port"
  $env:ALLOW_AGENT_EXECUTION = 'false'
  $env:ALLOW_PLATFORM_MUTATION = 'false'
  $env:ALLOW_DATABASE_ACCESS = 'false'
  $env:PYTHONPATH = (Join-Path $Worktree 'backend\src')

  $script:CurrentStage = 'WORKTREE_IMPORT_RESOLUTION'
  $importProbe = Get-ExternalText -Executable $python.path -Arguments @('-c', 'import pathlib, palwakf_local_agents.app as a; print(pathlib.Path(a.__file__).resolve())')
  $importPath = $importProbe.text
  if ($importProbe.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($importPath)) {
    throw "WORKTREE_IMPORT_RESOLUTION_FAILED: exit=$($importProbe.exit_code);output=$importPath"
  }
  if ($importPath -notlike "$Worktree*") { throw "WORKTREE_IMPORT_RESOLUTION_FAILED: $importPath" }
  Set-Content -LiteralPath (Join-Path $EvidenceRoot 'import_resolution.txt') -Value $importPath -Encoding UTF8

  $serviceStdout = Join-Path $LogRoot 'service.stdout.log'
  $serviceStderr = Join-Path $LogRoot 'service.stderr.log'
  $script:CurrentStage = 'FASTAPI_RUNTIME_START'
  Write-UatLog 'FASTAPI_RUNTIME=START'
  $serviceProcess = Start-Process -FilePath $python.path -ArgumentList @('-m', 'uvicorn', 'palwakf_local_agents.app:app', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory $Worktree -RedirectStandardOutput $serviceStdout -RedirectStandardError $serviceStderr -PassThru
  $baseUrl = "http://127.0.0.1:$Port"
  $health = Wait-ForHealth -BaseUrl $baseUrl
  Write-JsonFile -Value $health -Path (Join-Path $EvidenceRoot 'health.json')
  Write-UatLog 'FASTAPI_RUNTIME=PASS'

  $script:CurrentStage = 'HTTP_RUNTIME_UAT'
  $httpResults = @()
  $routePaths = @(
    '/health',
    '/api/agents',
    '/api/tasks',
    '/agent-console',
    '/agent-console/',
    '/agent-console/workspaces',
    '/agent-console/tasks',
    '/agent-console/projects',
    '/agent-console/evidence',
    '/agent-console/reviews',
    '/agent-console/tools',
    '/agent-console/diagnostics',
    '/agent-console/pilot-control'
  )
  foreach ($path in $routePaths) {
    $item = Invoke-HttpEvidence -Uri "$baseUrl$path" -Method 'GET'
    $httpResults += $item
    if ($item.status -ne 200 -or $item.set_cookie_present) { throw "HTTP_READ_ROUTE_FAILED_OR_SET_COOKIE_PRESENT: $path" }
  }
  foreach ($asset in $assetFiles) {
    $relativeAssetPath = "/agent-console/assets/$($asset.Name)"
    $item = Invoke-HttpEvidence -Uri "$baseUrl$relativeAssetPath" -Method 'GET'
    $httpResults += $item
    if ($item.status -ne 200 -or $item.set_cookie_present) { throw "HTTP_ASSET_FAILED_OR_SET_COOKIE_PRESENT: $relativeAssetPath" }
  }
  $executionDenied = Invoke-HttpEvidence -Uri "$baseUrl/api/tasks/UAT-NOOP/run" -Method 'POST'
  $httpResults += $executionDenied
  if ($executionDenied.status -ne 403) { throw 'AGENT_EXECUTION_NEGATIVE_UAT_FAILED.' }
  Write-JsonFile -Value $httpResults -Path (Join-Path $EvidenceRoot 'http_runtime_results.json')
  Write-UatLog 'HTTP_RUNTIME_UAT=PASS'

  $script:CurrentStage = 'HEADLESS_BROWSER_CAPTURE'
  $headlessCaptureSummary = @()
  $headlessProfile = Join-Path $Worktree 'browser-headless-profile'
  if (-not $SkipHeadlessCapture) {
    $captureRoutes = @('/agent-console/', '/agent-console/workspaces', '/agent-console/tasks', '/agent-console/evidence', '/agent-console/diagnostics')
    foreach ($path in $captureRoutes) {
      $safeName = ($path.Trim('/') -replace '/', '_')
      if (-not $safeName) { $safeName = 'agent_console' }
      $pngPath = Join-Path $CaptureRoot "$safeName.png"
      $domPath = Join-Path $CaptureRoot "$safeName.dom.html"
      $captureLog = Join-Path $LogRoot "headless_$safeName.log"
      Invoke-HeadlessBrowserCapture -Browser $browser -ProfileDirectory $headlessProfile -Uri "$baseUrl$path" -PngPath $pngPath -DomPath $domPath -LogPath $captureLog
      $headlessCaptureSummary += [pscustomobject]@{ route = $path; screenshot = (Split-Path -Leaf $pngPath); dom = (Split-Path -Leaf $domPath); result = 'PASS' }
    }
    Write-UatLog 'HEADLESS_BROWSER_RENDER_CAPTURE=PASS'
  }
  else {
    $headlessCaptureSummary += [pscustomobject]@{ route = $null; screenshot = $null; dom = $null; result = 'SKIPPED_BY_OPERATOR' }
  }
  Write-JsonFile -Value $headlessCaptureSummary -Path (Join-Path $EvidenceRoot 'browser_render_capture_manifest.json')

  $script:CurrentStage = 'VISIBLE_BROWSER_AND_HAR'
  $harPath = Join-Path $EvidenceRoot 'browser_network.har'
  if (-not $SkipVisibleBrowser) {
    $visibleProfile = Join-Path $Worktree 'browser-visible-profile'
    $visibleArguments = @("--user-data-dir=$visibleProfile", '--no-first-run', '--no-default-browser-check', '--new-window', "$baseUrl/agent-console/")
    $visibleBrowserProcess = Start-Process -FilePath $browser -ArgumentList $visibleArguments -PassThru
    Write-UatLog "VISIBLE_BROWSER_OPENED=$browser PID=$($visibleBrowserProcess.Id)"
  }

  if ((-not $NonInteractive) -and (-not $SkipVisibleBrowser)) {
    Write-Host ''
    Write-Host 'Manual HAR verification is required before continuing.' -ForegroundColor Cyan
    Write-Host '1) In the local console, navigate: Workspaces / Tasks / Evidence / Diagnostics.'
    Write-Host '2) Open DevTools > Network, enable Preserve log, reload the page, then export HAR to:'
    Write-Host ("   {0}" -f $harPath) -ForegroundColor Yellow
    Write-Host '3) React must not issue POST/PUT/PATCH/DELETE, Authorization, or Set-Cookie.'
    Write-Host '4) Close the isolated browser window, then press Enter to continue.'
    [void](Read-Host)
  }

  if (-not $SkipVisibleBrowser) {
    $script:CurrentStage = 'VISIBLE_BROWSER_PROFILE_CLEANUP'
    $visibleProfileCleanup = Stop-IsolatedBrowserProfileProcesses -BrowserExecutable $browser -ProfileDirectory $visibleProfile -Label 'visible_browser_profile'
    Write-JsonFile -Value $visibleProfileCleanup -Path (Join-Path $LogRoot 'visible_browser_profile_cleanup.json')
    Write-UatLog ("VISIBLE_BROWSER_PROFILE_CLEANUP=MATCHED:{0};STOPPED:{1};ERRORS:{2}" -f @($visibleProfileCleanup.matched_process_ids).Count, @($visibleProfileCleanup.stopped_process_ids).Count, @($visibleProfileCleanup.errors).Count)
  }

  $harResolution = Resolve-HarEvidence -EvidenceRoot $EvidenceRoot -CanonicalHarPath $harPath
  Write-JsonFile -Value $harResolution -Path (Join-Path $EvidenceRoot 'browser_network_har_resolution.json')
  if ($harResolution.result -eq 'AMBIGUOUS') {
    throw "HAR_FILENAME_AMBIGUOUS: $($harResolution.candidate_filenames -join ', ')"
  }

  $harSummary = Read-HarSummary -HarPath $harPath
  Write-JsonFile -Value $harSummary -Path (Join-Path $EvidenceRoot 'browser_network_har_summary.json')
  if ($harSummary.captured -and $harSummary.result -ne 'PASS') { throw "BROWSER_NETWORK_HAR_CONTRACT_FAILED: $($harSummary.result)" }

  $script:CurrentStage = 'POSTIMAGE_VERIFY'
  $postimageHashes = Get-Sha256Map -Root $Root -RelativePaths $trackedFiles
  Write-JsonFile -Value $postimageHashes -Path (Join-Path $EvidenceRoot 'source_postimage_sha256.json')
  foreach ($relative in $trackedFiles) {
    if ($preimageHashes[$relative] -ne $postimageHashes[$relative]) { throw "ORIGINAL_SOURCE_CODE_MUTATED_DURING_UAT: $relative" }
  }

  $status = if ($harSummary.result -eq 'PASS' -and -not $SkipHeadlessCapture) { 'ACCEPTED_LOCAL_RUNTIME_AND_BROWSER_EVIDENCE' } elseif (-not $SkipHeadlessCapture) { 'PARTIAL_ACCEPTANCE__HTTP_AND_RENDER_CAPTURE_PASS__HAR_PENDING' } else { 'PARTIAL_ACCEPTANCE__HTTP_PASS__BROWSER_CAPTURE_SKIPPED' }
  $reportLines = @(
    '# Windows Local Browser UAT Report',
    '',
    ("- Run ID: {0}" -f $runId),
    ("- Result: {0}" -f $status),
    ("- Bind: 127.0.0.1:{0}" -f $Port),
    '- Runtime safety: ALLOW_AGENT_EXECUTION=false, ALLOW_PLATFORM_MUTATION=false, ALLOW_DATABASE_ACCESS=false',
    '- Execution source: temporary isolated worktree; tracked source files remain unchanged.',
    '- HTTP read routes: PASS',
    '- React read-only static contract: PASS',
    '- Agent execution negative UAT: POST /api/tasks/UAT-NOOP/run = 403',
    ("- Browser screenshot/DOM capture: {0} routes passed" -f (@($headlessCaptureSummary | Where-Object { $_.result -eq 'PASS' }).Count)),
    ("- HAR filename resolution: {0}" -f $harResolution.result),
    ("- HAR: {0}" -f $harSummary.result),
    '',
    '## Acceptance decision',
    'This evidence does not enable React write, model execution, pilot, database or platform mutation, or production promotion.'
  )
  $report = $reportLines -join [Environment]::NewLine
  Set-Content -LiteralPath (Join-Path $EvidenceRoot 'BROWSER_UAT_RESULT.md') -Value $report -Encoding UTF8

  if (-not $RetainWorktree -and (Test-Path -LiteralPath $Worktree)) {
    $script:CurrentStage = 'WORKTREE_CLEANUP'
    if ($serviceProcess -and -not $serviceProcess.HasExited) {
      Stop-Process -Id $serviceProcess.Id -Force -ErrorAction SilentlyContinue
      $serviceProcess.WaitForExit(10000) | Out-Null
    }

    $headlessProfileCleanup = Stop-IsolatedBrowserProfileProcesses -BrowserExecutable $browser -ProfileDirectory $headlessProfile -Label 'headless_browser_profile'
    Write-JsonFile -Value $headlessProfileCleanup -Path (Join-Path $LogRoot 'headless_browser_profile_cleanup.json')
    if (-not $SkipVisibleBrowser) {
      $visibleProfileCleanup = Stop-IsolatedBrowserProfileProcesses -BrowserExecutable $browser -ProfileDirectory $visibleProfile -Label 'visible_browser_profile_final'
      Write-JsonFile -Value $visibleProfileCleanup -Path (Join-Path $LogRoot 'visible_browser_profile_cleanup_final.json')
    }

    $worktreeCleanup = Remove-IsolatedWorktreeWithRetries -Path $Worktree -LogRoot $LogRoot -MaxAttempts 5
    Write-JsonFile -Value $worktreeCleanup -Path (Join-Path $LogRoot 'worktree_cleanup_result.json')
    Write-UatLog 'WORKTREE_CLEANUP=PASS'
  }

  $script:CurrentStage = 'EVIDENCE_ARCHIVE'
  $evidenceFiles = @(
    Get-ChildItem -LiteralPath $EvidenceRoot -Recurse -File |
      Where-Object { $_.Name -ne 'runtime_evidence_manifest.json' } |
      ForEach-Object {
        [pscustomobject]@{
          path = $_.FullName.Substring($EvidenceRoot.Length).TrimStart('\')
          sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
          bytes = $_.Length
        }
      }
  )
  $runtimeManifest = [ordered]@{
    run_id = $runId
    result = $status
    evidence_root = $EvidenceRoot
    worktree_retained = [bool]$RetainWorktree
    health_safety_ok = [bool]$health.safety_ok
    http_route_count = $httpResults.Count
    http_set_cookie_count = @($httpResults | Where-Object { $_.set_cookie_present }).Count
    browser_capture_result_count = @($headlessCaptureSummary | Where-Object { $_.result -eq 'PASS' }).Count
    har_filename_resolution = $harResolution
    har = $harSummary
    original_source_tracked_hashes_unchanged = $true
    files = $evidenceFiles
  }
  Write-JsonFile -Value $runtimeManifest -Path (Join-Path $EvidenceRoot 'runtime_evidence_manifest.json')

  $archivePath = Join-Path (Split-Path -Parent $EvidenceRoot) "$runId.zip"
  Compress-Archive -Path (Join-Path $EvidenceRoot '*') -DestinationPath $archivePath -Force
  $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
  $archiveHashPath = "$archivePath.sha256.txt"
  Set-Content -LiteralPath $archiveHashPath -Value "$archiveHash  $(Split-Path -Leaf $archivePath)" -Encoding UTF8
  Write-UatLog "EVIDENCE_ARCHIVE=$archivePath"
  Write-UatLog "EVIDENCE_ARCHIVE_SHA256=$archiveHash"
  Write-UatLog "FINAL_RESULT=$status"
}
catch {
  $exceptionMessage = 'UNKNOWN_UAT_RUNNER_FAILURE'
  $exceptionType = 'Unknown'
  $stackTrace = ''
  if ($null -ne $_) {
    if ($null -ne $_.Exception) {
      $exceptionMessage = [string]$_.Exception.Message
      $exceptionType = $_.Exception.GetType().FullName
    }
    if ($null -ne $_.ScriptStackTrace) { $stackTrace = [string]$_.ScriptStackTrace }
  }

  $failureLines = @(
    "FINAL_RESULT=FAILED",
    "FAILED_STAGE=$script:CurrentStage",
    "EXCEPTION_TYPE=$exceptionType",
    "EXCEPTION_MESSAGE=$exceptionMessage",
    "SCRIPT_STACK=$stackTrace"
  )
  $failureText = $failureLines -join [Environment]::NewLine
  if ($EvidenceRoot -and (Test-Path -LiteralPath $EvidenceRoot)) {
    Set-Content -LiteralPath (Join-Path $EvidenceRoot 'FAILED.txt') -Value $failureText -Encoding UTF8
  }
  Write-Host $failureText -ForegroundColor Red
  exit 1
}
finally {
  if ($serviceProcess -and -not $serviceProcess.HasExited) {
    Stop-Process -Id $serviceProcess.Id -Force -ErrorAction SilentlyContinue
  }
  foreach ($key in $environmentKeys) {
    [Environment]::SetEnvironmentVariable($key, $originalEnvironment[$key], 'Process')
  }
}
