# Run PalEventDrop watcher (Infisical optional; else watcher-config.json or env).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (Get-Command infisical -ErrorAction SilentlyContinue) {
    # Store DISCORD_WEBHOOK_URL in Infisical (e.g. path /palworld). Override with INFISICAL_PATH.
    $path = if ($env:INFISICAL_PATH) { $env:INFISICAL_PATH } else { "/palworld" }
    infisical run --env=prod --path=$path -- python tools/event-watcher.py
    exit $LASTEXITCODE
}

python tools/event-watcher.py
