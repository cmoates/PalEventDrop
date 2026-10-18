# Write one valid test event into pending/ (atomic tmp -> rename).

$ErrorActionPreference = "Stop"



$root = if ($env:PALEVENTDROP_ROOT) { $env:PALEVENTDROP_ROOT } else {

    Join-Path $env:LOCALAPPDATA "Pal\Saved\PalEventDrop"

}

$pending = Join-Path $root "pending"

New-Item -ItemType Directory -Force -Path $pending | Out-Null



$stamp = Get-Date -Format "yyyyMMddHHmmss"

$id = "manual-test-$stamp"

$unix = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$name = "{0:D10}_manual.json" -f $unix

$payload = @{

    schema  = 1

    id      = $id

    ts      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    source  = "manual"

    type    = "test"

    title   = "PalEventDrop test"

    message = "Hello from write-test-event.ps1"

    payload = @{}

} | ConvertTo-Json -Compress



$final = Join-Path $pending $name

$tmp = "$final.tmp"

$utf8 = New-Object System.Text.UTF8Encoding $false

[System.IO.File]::WriteAllText($tmp, $payload, $utf8)

Move-Item -LiteralPath $tmp -Destination $final -Force



Write-Host "Wrote $final"

Write-Host "Watcher should move it to done/ and post to Apprise."

