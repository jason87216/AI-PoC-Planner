[CmdletBinding()]
param(
    [string]$ConfirmText = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

trap {
    Write-Host 'UAT 測試資料清除失敗，未完成清除。'
    exit 1
}

if ([string]::IsNullOrWhiteSpace($ConfirmText)) {
    Write-Host '這會刪除所有 UAT 專案、訪談、評估與報告。'
    Write-Host '模型設定會保留。'
    $ConfirmText = Read-Host '請輸入 RESET 以繼續'
}

if ($ConfirmText -cne 'RESET') {
    Write-Host '已取消，未刪除任何檔案。'
    exit 2
}

$localAppData = [Environment]::GetEnvironmentVariable('LOCALAPPDATA', 'Process')
if ([string]::IsNullOrWhiteSpace($localAppData)) {
    Write-Host 'UAT 測試資料清除失敗，未刪除任何檔案。'
    exit 1
}

$uatRoot = Join-Path $localAppData 'AI-PoC-Planner-UAT'
$stopScript = Join-Path $PSScriptRoot 'stop-local.ps1'

$null = & $stopScript -Mode Uat 2>&1
$stopExitCode = $LASTEXITCODE
if ($stopExitCode -ne 0) {
    Write-Host 'UAT runtime 無法安全停止，未刪除任何檔案。'
    exit $stopExitCode
}

foreach ($filename in @('planner.sqlite3', 'planner.sqlite3-wal', 'planner.sqlite3-shm')) {
    $target = Join-Path $uatRoot $filename
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Force
    }
}

Write-Host 'UAT 測試資料已清除，模型設定已保留。'
exit 0
