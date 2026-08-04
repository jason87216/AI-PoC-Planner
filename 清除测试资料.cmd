@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\reset-uat-data.ps1"
set "exitCode=%ERRORLEVEL%"
if "%exitCode%"=="0" (
    echo UAT 測試資料已清除，模型設定已保留。
) else if "%exitCode%"=="2" (
    echo 已取消，未刪除任何檔案。
) else (
    echo UAT 測試資料清除失敗，請查看安全提示。
)
pause
endlocal & exit /b %exitCode%
