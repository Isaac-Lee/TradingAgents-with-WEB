param([int]$Port = 8766)
$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $workspacePath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install the project first. See webapp/README.md.'
}
Push-Location -LiteralPath $workspacePath
try {
    & $pythonPath -m webapp.server --port $Port
} finally {
    Pop-Location
}
