# PalEventDrop

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

UE4SS **library mod** for [Palworld](https://store.steampowered.com/app/1623730/Palworld/). Producer mods call `_G.PalEventDrop.publish(event)`; each event becomes one JSON file in a **pending** folder on disk (atomic write, no locking between mods).

A small **Python watcher** on your gaming PC reads those files, sends notifications (e.g. Apprise → Matrix), then moves them to **done**.

## Requirements

- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) (Palworld experimental build)
- Palworld with UE4SS Lua mods enabled

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

Default root: `%LOCALAPPDATA%\Pal\Saved\PalEventDrop\` with subfolders `pending/`, `done/`, `failed/`.

```powershell
cd path\to\PalEventDrop
infisical run --env=prod --path=/matrix -- python tools\event-watcher.py
```

| Variable | Default |
|----------|---------|
| `PALEVENTDROP_ROOT` | `%LOCALAPPDATA%\Pal\Saved\PalEventDrop` |
| `PALEVENTDROP_STATE` | `...\PalEventDrop\watcher-state.json` |
| `APPRISE_NOTIFY_URL` | `https://apprise.moat.es/notify/palworld` |
| `APPRISE_API_KEY` | required |

Homelab Apprise/Matrix setup: [docs/homelab.md](docs/homelab.md). Optional wrapper: `tools/run-watcher.ps1`.

## Test drop (no game)

With the watcher running, create a file in `pending/`:

```json
{"schema":1,"id":"test-1","ts":"2026-01-01T00:00:00Z","source":"manual","type":"test","title":"Test","message":"Hello","payload":{}}
```

Use a unique filename such as `0000000001_test.json`.

## Writing a producer mod

1. Add `PalEventDrop : 1` above your mod in `mods.txt`.
2. After load, call `_G.PalEventDrop.publish({ source = "YourMod", type = "...", ... })`.
3. Ship only hooks + event mapping — no file I/O in your mod.

API surface: `_G.PalEventDrop.VERSION`, `.SCHEMA`, `.pending_dir()`, `.publish(event)` → `id, err`.

## License

MIT — see [LICENSE](LICENSE).
