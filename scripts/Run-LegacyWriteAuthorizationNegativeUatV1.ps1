[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$runId = 'LEGACY_WRITE_AUTH_NEGATIVE_UAT_' + (Get-Date -Format 'yyyyMMddTHHmmssZ')
$outRoot = Join-Path $ProjectRoot ('output\legacy_write_authorization_negative_uat\' + $runId)
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$stdout = Join-Path $outRoot 'pytest.stdout.log'
$stderr = Join-Path $outRoot 'pytest.stderr.log'
$priorPythonPath = $env:PYTHONPATH
$priorDontWrite = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONPATH = Join-Path $ProjectRoot 'backend\src'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location (Join-Path $ProjectRoot 'backend')
try {
  & $python -m pytest tests/test_legacy_write_authorization_negative_uat.py -q -p no:cacheprovider 1> $stdout 2> $stderr
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
  $env:PYTHONPATH = $priorPythonPath
  $env:PYTHONDONTWRITEBYTECODE = $priorDontWrite
}
if (Test-Path -LiteralPath $stdout) { Get-Content -LiteralPath $stdout }
if ((Test-Path -LiteralPath $stderr) -and ((Get-Item -LiteralPath $stderr).Length -gt 0)) { Get-Content -LiteralPath $stderr }
$evidence = [ordered]@{
  contract = 'LEGACY_WRITE_AUTHORIZATION_NEGATIVE_UAT_V1'
  run_id = $runId
  project_root = $ProjectRoot
  test_target = 'backend/tests/test_legacy_write_authorization_negative_uat.py'
  exit_code = $exitCode
  model_execution = 'NONE'
  react_write = 'NOT_ENABLED'
  platform_mutation = 'NOT_EXECUTED'
  database_access = 'TEST_TEMPORARY_ONLY'
}
$evidencePath = Join-Path $outRoot 'negative_uat_evidence.json'
$evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $evidencePath -Encoding UTF8
if ($exitCode -ne 0) {
  'NEGATIVE_UAT=FAIL'
  "EVIDENCE_ROOT=$outRoot"
  exit $exitCode
}
$archive = Join-Path (Split-Path -Parent $outRoot) ($runId + '.zip')
Compress-Archive -Path (Join-Path $outRoot '*') -DestinationPath $archive -Force
$archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
"EVIDENCE_ROOT=$outRoot"
"EVIDENCE_ARCHIVE=$archive"
"EVIDENCE_ARCHIVE_SHA256=$archiveHash"
'NEGATIVE_UAT=PASS'
