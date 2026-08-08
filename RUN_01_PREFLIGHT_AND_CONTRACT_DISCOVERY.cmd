@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_01_PREFLIGHT_AND_CONTRACT_DISCOVERY.ps1"
exit /b %ERRORLEVEL%
