# Drop a synthetic expedition_complete event (same shape as ExpeditionNotifier in-game).
$ErrorActionPreference = "Stop"

$root = if ($env:PALEVENTDROP_ROOT) { $env:PALEVENTDROP_ROOT } else {
    Join-Path $env:LOCALAPPDATA "Pal\Saved\PalEventDrop"
}
$pending = Join-Path $root "pending"
New-Item -ItemType Directory -Force -Path $pending | Out-Null

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$id = "expedition-test-$stamp"
$unix = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$name = "{0:D10}_expedition.json" -f $unix

$payload = @{
    schema  = 1
    id      = $id
    ts      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    source  = "ExpeditionNotifier"
    type    = "expedition_complete"
    title   = "Expedition complete"
    message = "Test expedition returned with loot (write-test-expedition.ps1)"
    payload = @{}
} | ConvertTo-Json -Compress

$final = Join-Path $pending $name
$tmp = "$final.tmp"
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($tmp, $payload, $utf8)
Move-Item -LiteralPath $tmp -Destination $final -Force

Write-Host "Wrote $final"
Write-Host "Expect green expedition embed in Discord when watcher is running."
