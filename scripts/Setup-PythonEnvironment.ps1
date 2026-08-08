[CmdletBinding()]
param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $py) { throw "PYTHON_LAUNCHER_NOT_FOUND" }

Push-Location $ProjectRoot
try {
  & py -3.11 -m venv .venv
  if ($LASTEXITCODE -ne 0) { & py -3.12 -m venv .venv }
  if ($LASTEXITCODE -ne 0) { throw "PYTHON_311_OR_312_REQUIRED" }

  $python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
  & $python -m pip install --upgrade pip
  & $python -m pip install -e ".[dev]"
  Write-Host "PYTHON_ENV_STATUS=COMPLETE"
  Write-Host "PLATFORM_MUTATION=NONE"
  Write-Host "DATABASE_ACCESS=NONE"
}
finally {
  Pop-Location
}
