param(
  [Parameter(Mandatory=$true)][string]$PythonExe,
  [Parameter(Mandatory=$true)][string]$ConfigPath
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'PYTHON_EXE_NOT_FOUND' }
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw 'CONFIG_NOT_FOUND' }
$resolvedPython = (Resolve-Path -LiteralPath $PythonExe).Path
$resolvedConfig = (Resolve-Path -LiteralPath $ConfigPath).Path
$env:PALWAKF_EXECUTOR_CONFIG = $resolvedConfig
& $resolvedPython -c "import win32serviceutil, palwakf_local_agents.windows_service_v1" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_DEPENDENCY_PREFLIGHT_FAILED' }
& $resolvedPython -m palwakf_local_agents.windows_service_v1 --startup auto install
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_INSTALL_FAILED' }
sc.exe failure PalWakfOutboundLocalExecutorV1 reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'WINDOWS_SERVICE_RECOVERY_POLICY_FAILED' }
[Environment]::SetEnvironmentVariable('PALWAKF_EXECUTOR_CONFIG', $resolvedConfig, 'Machine')
Start-Service -Name PalWakfOutboundLocalExecutorV1
Get-Service -Name PalWakfOutboundLocalExecutorV1 | Select-Object Name,Status,StartType
