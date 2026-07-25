param([ValidateSet('Local', 'Uat')][string]$Mode = 'Local')
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Project virtual environment is missing: $python"
    exit 2
}
& $python -m ai_poc_planner.local_runtime stop --mode $Mode.ToLowerInvariant()
exit $LASTEXITCODE
