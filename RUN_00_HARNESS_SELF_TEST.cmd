@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_00_HARNESS_SELF_TEST.ps1"
exit /b %ERRORLEVEL%
