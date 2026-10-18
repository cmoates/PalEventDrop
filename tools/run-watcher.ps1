# Run PalEventDrop watcher with Infisical (adjust path/env if needed).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (Get-Command infisical -ErrorAction SilentlyContinue) {
    infisical run --env=prod --path=/matrix -- python tools/event-watcher.py
    exit $LASTEXITCODE
}

if (-not $env:APPRISE_API_KEY) {
    Write-Error "Set APPRISE_API_KEY or install Infisical CLI (see README)."
}
python tools/event-watcher.py
