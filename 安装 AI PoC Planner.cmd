@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "exitCode=%ERRORLEVEL%"
echo.
if "%exitCode%"=="0" (
    echo 安装完成。现在可以双击“启动 AI PoC Planner.cmd”。
) else (
    echo 安装未完成，请查看上方提示。
)
pause
endlocal & exit /b %exitCode%
