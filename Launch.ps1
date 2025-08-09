param(
  [string]$User,          # Optional: overrides config.ini (env var)
  [string]$Pass,          # Optional: overrides config.ini (env var)
  [switch]$Playwright,    # Force re-run playwright install
  [switch]$Update         # Force pip install -r requirements.txt
)

$ErrorActionPreference = "Stop"

# --- locate repo root
$root = $PSScriptRoot
if (-not $root) { $root = Split-Path -Parent $MyInvocation.MyCommand.Definition }
Set-Location $root

Write-Host "== MissionchiefBot-X launcher =="

# --- ensure venv
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "Creating venv with Python 3.13..."
  & py -3.13 -m venv .venv
}

# --- upgrade pip, install requirements
Write-Host "Upgrading pip..."
& $venvPy -m pip install --upgrade pip

if ($Update -or $true) {
  Write-Host "Installing requirements..."
  & $venvPy -m pip install -r requirements.txt
}

# --- playwright browsers (idempotent)
if ($Playwright -or $true) {
  Write-Host "Ensuring Playwright browsers are installed..."
  & $venvPy -m playwright install
}

# --- first run convenience: copy config.sample.ini if config.ini absent
if (-not (Test-Path "config.ini") -and (Test-Path "config.sample.ini")) {
  Copy-Item "config.sample.ini" "config.ini"
  Write-Host "Copied config.sample.ini -> config.ini (edit as needed)."
}

# --- optional credentials via params override config.ini
if ($User) { $env:MISSIONCHIEF_USER = $User }
if ($Pass) { $env:MISSIONCHIEF_PASS = $Pass }

# --- unbuffered logs
$env:PYTHONUNBUFFERED = "1"

# --- run
Write-Host "Starting bot..."
& $venvPy -u -X dev Main.py
exit $LASTEXITCODE
