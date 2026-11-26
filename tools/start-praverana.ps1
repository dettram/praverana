$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found. Install it first: https://docs.astral.sh/uv/"
    exit 1
}

$store = Join-Path $env:USERPROFILE ".stroy-audit"
if (-not (Test-Path $store)) {
    Write-Host "WARNING: $store not found. Build the corpus index first:"
    Write-Host "  uv run --locked python scripts/build_index.py"
    Write-Host "  uv run --locked python scripts/build_clauses.py"
}

if (-not (Test-Path (Join-Path $root ".venv"))) {
    Write-Host "Installing locked dependencies..."
    uv sync --locked
}

Start-Job { Start-Sleep -Seconds 2; Start-Process "http://127.0.0.1:8765/app" } | Out-Null
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "app\server.py")
