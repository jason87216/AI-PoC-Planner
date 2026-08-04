@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\reset-uat-data.ps1"
set "exitCode=%ERRORLEVEL%"
echo.
pause
endlocal & exit /b %exitCode%
