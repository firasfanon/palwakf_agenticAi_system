param(
  [Parameter(Mandatory=$true)][string]$RepoRoot,
  [Parameter(Mandatory=$true)][string]$Python312Exe,
  [Parameter(Mandatory=$true)][string]$ConfigPath
)
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$python = (Resolve-Path -LiteralPath $Python312Exe).Path
$config = (Resolve-Path -LiteralPath $ConfigPath).Path

if (-not (Test-Path -LiteralPath (Join-Path $repo 'pyproject.toml'))) { throw 'REPO_PYPROJECT_NOT_FOUND' }

$version = & $python -c "import sys; print('.'.join(map(str,sys.version_info[:2])))"
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne '3.12') { throw "PYTHON_3_12_REQUIRED:$version" }

$venv = Join-Path $repo '.venv-outbound-executor-v1'
$venvPython = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
  & $python -m venv $venv
  if ($LASTEXITCODE -ne 0) { throw 'VENV_CREATE_FAILED' }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'PIP_UPGRADE_FAILED' }

& $venvPython -m pip install -e "$repo[windows]"
if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_INSTALL_FAILED' }

& $venvPython -c "import win32serviceutil, cryptography, palwakf_local_agents.windows_service_v1"
if ($LASTEXITCODE -ne 0) { throw 'SERVICE_DEPENDENCY_PREFLIGHT_FAILED' }

[Environment]::SetEnvironmentVariable('PALWAKF_EXECUTOR_CONFIG', $config, 'Machine')
$env:PALWAKF_EXECUTOR_CONFIG = $config

$existing = Get-Service -Name PalWakfOutboundLocalExecutorV1 -ErrorAction SilentlyContinue
if (-not $existing) {
  & $venvPython -m palwakf_local_agents.windows_service_v1 --startup auto install
  if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_INSTALL_FAILED' }
}

sc.exe config PalWakfOutboundLocalExecutorV1 start= auto | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_AUTOSTART_CONFIG_FAILED' }

sc.exe failure PalWakfOutboundLocalExecutorV1 reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_RECOVERY_POLICY_FAILED' }

Start-Service -Name PalWakfOutboundLocalExecutorV1 -ErrorAction Stop
Start-Sleep -Seconds 3
$svc = Get-Service -Name PalWakfOutboundLocalExecutorV1 -ErrorAction Stop
if ($svc.Status -ne 'Running') { throw "WINDOWS_SERVICE_NOT_RUNNING:$($svc.Status)" }

[pscustomobject]@{
  Bootstrap = 'PASS'
  RepoRoot = $repo
  Python = $venvPython
  ServiceName = $svc.Name
  Status = $svc.Status.ToString()
  StartType = $svc.StartType.ToString()
  ConfigSet = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable('PALWAKF_EXECUTOR_CONFIG','Machine'))
  ManualTerminalInterventionsPerTaskTarget = 0
}
