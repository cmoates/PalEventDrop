# PalEventDrop

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

UE4SS **library mod** for [Palworld](https://store.steampowered.com/app/1623730/Palworld/). Producer mods call `_G.PalEventDrop.publish(event)`; each event becomes one JSON file in a **pending** folder on disk (atomic write, no locking between mods).

A small **Python watcher** on your gaming PC reads those files, posts to a **Discord channel webhook**, then moves them to **done**.

## Requirements

- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) (Palworld experimental build)
- Palworld with UE4SS Lua mods enabled
- Python 3.10+ on the PC where you run the watcher
- A Discord **channel webhook** ([create one](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) in Server Settings → Integrations)

## Install

Clone or download this repo, then copy this folder’s contents (`Scripts/`, `Info.json`, etc.) to:

```
Palworld/Pal/Binaries/Win64/ue4ss/Mods/PalEventDrop/
```

Enable **before** any producer mod in `mods.txt`:

```txt
PalEventDrop : 1
```

Example producer: **[ExpeditionNotifier](https://github.com/cmoates/ExpeditionNotifier)** (expedition-complete notifications).

## Producer API

```lua
local id, err = _G.PalEventDrop.publish({
    source = "MyMod",
    type = "my_event",
    title = "Optional title",
    message = "Body text",
    payload = { key = "value" }, -- optional; string/number/bool values only
})
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for folder layout, schema, and watcher contract.

## Watcher (gaming PC)

Default event root: `%LOCALAPPDATA%\Pal\Saved\PalEventDrop\` (`pending/`, `processing/`, `done/`, `failed/`). Run **one** watcher process at a time.

### Discord webhook (pick one)

**A — Config file (no Infisical)** — copy the example and edit:

```powershell
Copy-Item tools\watcher-config.example.json "$env:LOCALAPPDATA\Pal\Saved\PalEventDrop\watcher-config.json"
# Edit watcher-config.json and paste your webhook URL (keep this file private; do not commit it)
```

**B — Environment variable**

```powershell
$env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
python tools\event-watcher.py
```

**C — Infisical** (optional): store `DISCORD_WEBHOOK_URL` under e.g. `/palworld`, then:

```powershell
.\tools\run-watcher.ps1
```

Or: `infisical run --env=prod --path=/palworld -- python tools\event-watcher.py`

Env overrides config file. Config path override: `PALEVENTDROP_WATCHER_CONFIG`.

| Variable | Purpose |
|----------|---------|
| `DISCORD_WEBHOOK_URL` | Discord channel webhook (preferred via Infisical or env) |
| `DISCORD_WEBHOOK_USERNAME` | Optional display name for webhook posts |
| `PALEVENTDROP_ROOT` | Event folder root (default `%LOCALAPPDATA%\Pal\Saved\PalEventDrop`) |
| `PALEVENTDROP_STATE` | Idempotency state file (default `...\watcher-state.json`) |
| `PALEVENTDROP_WATCHER_CONFIG` | Path to JSON config if not using default under event root |
| `INFISICAL_PATH` | Infisical secret path for `run-watcher.ps1` (default `/palworld`) |

**Never commit webhook URLs** — they are full channel write credentials.

## Test drop (no game)

With the watcher running:

```powershell
.\tools\write-test-event.ps1
```

Or paste JSON into a **new** file under `pending/` and save once (do not leave a 0-byte file while the watcher is running). Example body:

```json
{"schema":1,"id":"test-1","ts":"2026-01-01T00:00:00Z","source":"manual","type":"test","title":"Test","message":"Hello","payload":{}}
```

## Writing a producer mod

1. Add `PalEventDrop : 1` above your mod in `mods.txt`.
2. After load, call `_G.PalEventDrop.publish({ source = "YourMod", type = "...", ... })`.
3. Ship only hooks + event mapping — no file I/O in your mod.

API surface: `_G.PalEventDrop.VERSION`, `.SCHEMA`, `.pending_dir()`, `.publish(event)` → `id, err`.

## License

MIT — see [LICENSE](LICENSE).
