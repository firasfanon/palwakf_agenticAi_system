@echo off
if "%~1"=="" (
  echo NEW_RETRY_AUTHORIZATION_TOKEN_REQUIRED
  exit /b 20
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_02_EXECUTE_AUTHORIZED_LIVE_PROBE.ps1" -AuthorizationToken "%~1"
exit /b %ERRORLEVEL%
