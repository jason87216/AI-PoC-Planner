@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\status-local.ps1" -Mode Uat
set "exitCode=%ERRORLEVEL%"
echo.
pause
endlocal & exit /b %exitCode%
