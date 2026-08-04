@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1" -Mode Uat
set "exitCode=%ERRORLEVEL%"
endlocal & exit /b %exitCode%
