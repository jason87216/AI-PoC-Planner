@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "exitCode=%ERRORLEVEL%"
echo.
pause
endlocal & exit /b %exitCode%
