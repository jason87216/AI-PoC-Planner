[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$venvRoot = Join-Path $ProjectRoot '.venv'
$venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

function Fail-Setup {
    param([Parameter(Mandatory)][string]$Message)

    Write-Host ''
    Write-Host "[SETUP FAILED] $Message" -ForegroundColor Red
    exit 1
}

function Test-Python312 {
    param(
        [Parameter(Mandatory)][string]$Command,
        [string[]]$Arguments = @()
    )

    try {
        $versionLines = & $Command @Arguments --version 2>&1
        $exitCode = $LASTEXITCODE
        $version = ($versionLines -join ' ').Trim()
        return $exitCode -eq 0 -and $version -match '^Python 3\.12\.'
    }
    catch {
        return $false
    }
}

Write-Host 'AI PoC Planner Windows portfolio quickstart'
Write-Host "Project directory: $ProjectRoot"

$pythonCommand = ''
$pythonArguments = @()

if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    if (-not (Test-Python312 -Command $venvPython)) {
        Fail-Setup "The existing .venv is not using Python 3.12. This setup will not replace it. Remove or move that environment manually, then run setup.ps1 again."
    }
    Write-Host 'Existing Python 3.12 virtual environment found; reusing it.'
}
else {
    $pyLauncher = Get-Command -Name 'py.exe' -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher -and (Test-Python312 -Command $pyLauncher.Source -Arguments @('-3.12'))) {
        $pythonCommand = $pyLauncher.Source
        $pythonArguments = @('-3.12')
    }
    else {
        $pythonOnPath = Get-Command -Name 'python.exe' -ErrorAction SilentlyContinue
        if ($null -ne $pythonOnPath -and (Test-Python312 -Command $pythonOnPath.Source)) {
            $pythonCommand = $pythonOnPath.Source
        }
    }

    if ([string]::IsNullOrWhiteSpace($pythonCommand)) {
        Fail-Setup 'Compatible Python 3.12 was not found. Install Python 3.12 for Windows from https://www.python.org/downloads/windows/, then open a new terminal and run setup.ps1 again. This script does not install system Python or modify PATH.'
    }

    Write-Host 'Creating project-local .venv with Python 3.12...'
    & $pythonCommand @pythonArguments -m venv $venvRoot
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        Fail-Setup 'Creating .venv failed. Confirm that Python 3.12 is available and that this project directory is writable, then run setup.ps1 again.'
    }
}

Write-Host 'Installing AI PoC Planner runtime dependencies into .venv...'
& $venvPython -m pip install --disable-pip-version-check --no-input -e $ProjectRoot
if ($LASTEXITCODE -ne 0) {
    Fail-Setup 'Dependency installation failed. Check the pip output above, confirm network access to the Python package index, and run setup.ps1 again. The existing .venv was kept.'
}

Write-Host ''
Write-Host 'Setup completed successfully.' -ForegroundColor Green
Write-Host 'Start:  double-click "启动 AI PoC Planner.cmd"'
Write-Host 'Status: double-click "查看运行状态.cmd"'
Write-Host 'Stop:   double-click "关闭 AI PoC Planner.cmd"'
