[CmdletBinding()]
param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
  [int]$Port = 8765
)

$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw "PYTHON_ENV_NOT_READY_RUN_SETUP_FIRST" }

$env:LOCAL_AGENT_HOST = '127.0.0.1'
$env:LOCAL_AGENT_PORT = "$Port"
$env:ALLOW_AGENT_EXECUTION = 'false'
$env:ALLOW_PLATFORM_MUTATION = 'false'
$env:ALLOW_DATABASE_ACCESS = 'false'

Push-Location $ProjectRoot
try {
  & $python -m uvicorn palwakf_local_agents.app:app --app-dir backend\src --host 127.0.0.1 --port $Port
}
finally {
  Pop-Location
}
