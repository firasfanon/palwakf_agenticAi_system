param(
  [Parameter(Mandatory=$true)][string]$RepoRoot,
  [Parameter(Mandatory=$true)][string]$ConfigPath,
  [string]$MachinePythonExe = "C:\Program Files\Python311\python.exe"
)
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$config = (Resolve-Path -LiteralPath $ConfigPath).Path
$python = (Resolve-Path -LiteralPath $MachinePythonExe).Path
$svcName = 'PalWakfOutboundLocalExecutorV1'
$svcKey = "HKLM:\SYSTEM\CurrentControlSet\Services\$svcName"

if (-not (Test-Path -LiteralPath (Join-Path $repo 'pyproject.toml'))) {
  throw 'REPO_PYPROJECT_NOT_FOUND'
}

$version = (& $python -c "import sys; print('.'.join(map(str,sys.version_info[:2])))").Trim()
if ($LASTEXITCODE -ne 0 -or $version -notin @('3.11','3.12')) {
  throw "SUPPORTED_MACHINE_PYTHON_REQUIRED:$version"
}

$basePrefix = (& $python -c "import sys; print(sys.base_prefix)").Trim()
if ($python -like 'C:\Users\*' -or $basePrefix -like 'C:\Users\*') {
  throw "MACHINE_PYTHON_MUST_NOT_BE_USER_SCOPED:$python|$basePrefix"
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'PIP_UPGRADE_FAILED' }

& $python -m pip install --upgrade "$repo[windows]"
if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_INSTALL_FAILED' }

$postinstall = Join-Path (Split-Path -Parent $python) 'Scripts\pywin32_postinstall.exe'
if (-not (Test-Path -LiteralPath $postinstall)) {
  throw "PYWIN32_POSTINSTALL_EXE_NOT_FOUND:$postinstall"
}

& $postinstall -install -silent
if ($LASTEXITCODE -ne 0) { throw 'PYWIN32_POSTINSTALL_FAILED' }

& $python -c "import servicemanager, win32service, win32serviceutil, pywintypes, cryptography; import palwakf_local_agents.windows_service_v1 as s; assert s.PalWakfOutboundExecutorService is not None; print('GLOBAL_SERVICE_HOST_IMPORT=PASS')"
if ($LASTEXITCODE -ne 0) { throw 'SERVICE_HOST_IMPORT_PREFLIGHT_FAILED' }

$serviceExeOutput = @(
  & $python -c "import win32serviceutil; print(win32serviceutil.LocatePythonServiceExe())"
)
if ($LASTEXITCODE -ne 0) {
  throw "PYTHONSERVICE_EXE_DISCOVERY_FAILED:$LASTEXITCODE"
}

$serviceExeCandidates = @(
  $serviceExeOutput |
    ForEach-Object { "$_".Trim() } |
    Where-Object {
      $_ -and
      (Test-Path -LiteralPath $_ -PathType Leaf)
    }
)

if ($serviceExeCandidates.Count -eq 0) {
  throw "PYTHONSERVICE_EXE_NOT_FOUND:$($serviceExeOutput -join ' | ')"
}

$serviceExe = $serviceExeCandidates[-1]

if (-not (Test-Path -LiteralPath $serviceExe -PathType Leaf)) {
  throw "PYTHONSERVICE_EXE_NOT_FOUND:$serviceExe"
}
if ($serviceExe -like 'C:\Users\*' -or $serviceExe -like '*\.venv*') {
  throw "PYTHONSERVICE_EXE_NOT_MACHINE_GLOBAL:$serviceExe"
}

[Environment]::SetEnvironmentVariable('PALWAKF_EXECUTOR_CONFIG', $config, 'Machine')
$env:PALWAKF_EXECUTOR_CONFIG = $config

$existing = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if ($existing) {
  if ($existing.Status -ne 'Stopped') {
    Stop-Service -Name $svcName -ErrorAction Stop
  }
  & $python -m palwakf_local_agents.windows_service_v1 --startup auto update
  if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_UPDATE_FAILED' }
} else {
  & $python -m palwakf_local_agents.windows_service_v1 --startup auto install
  if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_INSTALL_FAILED' }
}

if (-not (Test-Path -LiteralPath $svcKey)) {
  throw 'SERVICE_REGISTRY_KEY_NOT_FOUND'
}

New-ItemProperty -Path $svcKey -Name Environment -PropertyType MultiString -Value @(
  "PALWAKF_EXECUTOR_CONFIG=$config"
) -Force | Out-Null

sc.exe config $svcName start= auto | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_AUTOSTART_CONFIG_FAILED' }

sc.exe failure $svcName reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_RECOVERY_POLICY_FAILED' }

$imagePath = (Get-ItemProperty -Path $svcKey).ImagePath
$imagePathNormalized = $imagePath.Trim('"')
if ($imagePathNormalized -like 'C:\Users\*' -or $imagePathNormalized -like '*\.venv*') {
  throw "SERVICE_IMAGE_PATH_NOT_MACHINE_GLOBAL:$imagePath"
}
if (-not [string]::Equals(
  $imagePathNormalized,
  $serviceExe,
  [System.StringComparison]::OrdinalIgnoreCase
)) {
  throw "SERVICE_IMAGE_PATH_UNEXPECTED:$imagePath|EXPECTED:$serviceExe"
}

Start-Service -Name $svcName -ErrorAction Stop
Start-Sleep -Seconds 5

$svc = Get-Service -Name $svcName -ErrorAction Stop
if ($svc.Status -ne 'Running') {
  throw "WINDOWS_SERVICE_NOT_RUNNING:$($svc.Status)"
}

$probe = Join-Path $env:TEMP 'palwakf_bootstrap_transport_health.py'
@'
import json
from palwakf_local_agents.outbound_worker_v1 import load_worker_config
from palwakf_local_agents.github_issue_transport_v1 import GitHubIssueTransportV1

config = load_worker_config(
    r"C:\ProgramData\PalWakf\outbound_executor_v1\config.json"
)
print(json.dumps(GitHubIssueTransportV1(config.transport).health(), sort_keys=True))
'@ | Set-Content -LiteralPath $probe -Encoding UTF8

try {
  $health = @(& $python $probe)
  if ($LASTEXITCODE -ne 0) { throw 'OUTBOUND_TRANSPORT_HEALTH_FAILED' }
}
finally {
  Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
}

[pscustomobject]@{
  Bootstrap = 'PASS'
  RepoRoot = $repo
  Python = $python
  PythonBasePrefix = $basePrefix
  PyWin32PostInstall = $postinstall
  ServiceExecutable = $serviceExe
  ServiceName = $svc.Name
  Status = $svc.Status.ToString()
  StartType = $svc.StartType.ToString()
  TransportHealth = ($health -join '')
  ConfigSet = -not [string]::IsNullOrWhiteSpace(
    [Environment]::GetEnvironmentVariable('PALWAKF_EXECUTOR_CONFIG','Machine')
  )
  ManualTerminalInterventionsPerTaskTarget = 0
}
