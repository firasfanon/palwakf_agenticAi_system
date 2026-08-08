[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$ProjectRoot,
  [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
  $OutputRoot = Join-Path $ProjectRoot 'output\legacy_test_contract_migration_positive_authorization_uat'
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)

function Write-Stage([string]$Stage, [string]$Value) {
  Write-Output ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + "  $Stage=$Value")
}

function Invoke-LoggedProcess {
  param(
    [Parameter(Mandatory = $true)][string]$FileName,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$LogFile
  )
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $FileName
  $psi.Arguments = ($Arguments -join ' ')
  $psi.WorkingDirectory = $WorkingDirectory
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $psi
  [void]$process.Start()
  $stdout = $process.StandardOutput.ReadToEnd()
  $stderr = $process.StandardError.ReadToEnd()
  $process.WaitForExit()
  @(
    "COMMAND=$FileName $($psi.Arguments)",
    "EXIT_CODE=$($process.ExitCode)",
    '--- STDOUT ---',
    $stdout,
    '--- STDERR ---',
    $stderr
  ) | Set-Content -LiteralPath $LogFile -Encoding UTF8
  if ($process.ExitCode -ne 0) { throw "EXTERNAL_COMMAND_FAILED: $FileName EXIT=$($process.ExitCode) LOG=$LogFile" }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "PROJECT_ROOT_NOT_FOUND: $ProjectRoot" }
$venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$python = $null
if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $python = $venvPython }
if ($null -eq $python) {
  $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($null -ne $pythonCommand) { $python = $pythonCommand.Source }
}
if ([string]::IsNullOrWhiteSpace($python)) { throw 'PYTHON_EXECUTABLE_NOT_FOUND' }

$runId = 'LEGACY_TEST_CONTRACT_POSITIVE_AUTH_UAT_' + (Get-Date -Format 'yyyyMMddTHHmmssZ')
$runRoot = Join-Path $OutputRoot $runId
$worktree = Join-Path $runRoot 'isolated_worktree'
$logs = Join-Path $runRoot 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
Write-Stage 'RUN_ID' $runId
Write-Stage 'PROJECT_ROOT' $ProjectRoot
Write-Stage 'OUTPUT_ROOT' $runRoot
Write-Stage 'PYTHON_SELECTED' $python

try {
  $robocopyArgs = @($ProjectRoot, $worktree, '/E', '/XD', '.git', '.venv', 'node_modules', 'output', 'backups', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
  & robocopy.exe @robocopyArgs | Out-Null
  if ($LASTEXITCODE -gt 7) { throw "ISOLATED_WORKTREE_COPY_FAILED: ROBOCOPY_EXIT=$LASTEXITCODE" }
  Write-Stage 'ISOLATED_WORKTREE_COPY' 'PASS'

  $targetedLog = Join-Path $logs 'targeted_authorization_uat.log'
  Invoke-LoggedProcess -FileName $python -Arguments @('-m','pytest','-q','backend/tests/test_legacy_write_authorization_negative_uat.py','backend/tests/test_legacy_write_authorization_positive_uat.py') -WorkingDirectory $worktree -LogFile $targetedLog
  Write-Stage 'TARGETED_NEGATIVE_AND_POSITIVE_UAT' 'PASS'

  $fullLog = Join-Path $logs 'full_backend_suite.log'
  Invoke-LoggedProcess -FileName $python -Arguments @('-m','pytest','-q','backend/tests') -WorkingDirectory $worktree -LogFile $fullLog
  Write-Stage 'FULL_BACKEND_SUITE' 'PASS'

  $manifest = [ordered]@{
    contract = 'LEGACY_TEST_CONTRACT_MIGRATION_AND_CONTROLLED_POSITIVE_AUTHORIZATION_UAT_V1'
    run_id = $runId
    result = 'PASS'
    source_project_mutation = 'NONE'
    execution_scope = 'ISOLATED_WORKTREE_ONLY'
    targeted_negative_uat = 'PASS'
    controlled_positive_authorization_uat = 'PASS'
    full_backend_suite = 'PASS'
    react_write = 'NOT_ENABLED'
    model_execution = 'NOT_EXECUTED'
    pilot_execution = 'NOT_EXECUTED'
    commercial_positive_uat = 'NOT_EXECUTED'
  }
  $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $runRoot 'evidence_manifest.json') -Encoding UTF8

  $archive = Join-Path $OutputRoot ($runId + '.zip')
  Compress-Archive -Path (Join-Path $runRoot '*') -DestinationPath $archive -Force
  $archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToUpperInvariant()
  Set-Content -LiteralPath ($archive + '.sha256.txt') -Encoding ASCII -Value $archiveHash
  Write-Stage 'EVIDENCE_ARCHIVE' $archive
  Write-Stage 'EVIDENCE_ARCHIVE_SHA256' $archiveHash
  Write-Stage 'FINAL_RESULT' 'PASS'
}
catch {
  Write-Output 'FINAL_RESULT=FAILED'
  Write-Output 'FAILED_STAGE=LEGACY_TEST_CONTRACT_MIGRATION_OR_POSITIVE_UAT'
  Write-Output ('EXCEPTION_TYPE=' + $_.Exception.GetType().FullName)
  Write-Output ('EXCEPTION_MESSAGE=' + $_.Exception.Message)
  Write-Output ('SCRIPT_STACK=' + $_.ScriptStackTrace)
  exit 1
}
finally {
  if (Test-Path -LiteralPath $worktree) {
    Remove-Item -LiteralPath $worktree -Recurse -Force -ErrorAction SilentlyContinue
  }
}
