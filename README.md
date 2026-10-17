# PalMaildir

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

UE4SS **library mod** for [Palworld](https://store.steampowered.com/app/1623730/Palworld/). Producers call `_G.PalMaildir.publish(event)`; each event becomes one JSON file under a **maildir-style** `new/` folder (atomic write, no locking between mods).

External tools (see `tools/palmail-watcher.py`) move delivered files to `proc/` and notify Apprise/Matrix (or any other consumer you write).

## Requirements

- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) (Palworld experimental build)
- Palworld with UE4SS Lua mods enabled

## Install

Clone or download this repo, then copy `PalMaildir/` (this folder’s contents: `Scripts/`, `Info.json`, etc.) to:

```
Palworld/Pal/Binaries/Win64/ue4ss/Mods/PalMaildir/
```

Enable **before** any producer mod in `mods.txt`:

```txt
PalMaildir : 1
```

Example producer: **PalNotifyExpedition** (expedition-complete notifications; separate mod that depends on this library).
## Producer API

```lua
local id, err = _G.PalMaildir.publish({
    source = "MyMod",
    type = "my_event",
    title = "Optional title",
    message = "Body text",
    payload = { key = "value" }, -- optional; string/number/bool values only
})
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for layout, schema, and consumer contract.

## Watcher (gaming PC)

Creates `new/`, `proc/`, and `failed/` under `%LOCALAPPDATA%\Pal\Saved\PalMaildir\`.

```powershell
cd path\to\PalMaildir
infisical run --env=prod --path=/matrix -- python tools\palmail-watcher.py
```

| Variable | Default |
|----------|---------|
| `PALMAILDIR_ROOT` | `%LOCALAPPDATA%\Pal\Saved\PalMaildir` |
| `PALMAILDIR_STATE` | `...\PalMaildir\watcher-state.json` |
| `APPRISE_NOTIFY_URL` | `https://apprise.moat.es/notify/palworld` |
| `APPRISE_API_KEY` | required |

## Test drop (no game)

With the watcher running, create a file in `new/`:

```json
{"schema":1,"id":"test-1","ts":"2026-01-01T00:00:00Z","source":"manual","type":"test","title":"Test","message":"Hello","payload":{}}
```

Use a unique filename such as `0000000001_test.json`.

## Writing a producer mod

1. Add `PalMaildir : 1` above your mod in `mods.txt`.
2. After load, call `_G.PalMaildir.publish({ source = "YourMod", type = "...", ... })`.
3. Ship only hooks + event mapping — no file I/O in your mod.

API surface: `_G.PalMaildir.VERSION`, `.SCHEMA`, `.publish(event)` → `id, err`.

## License

MIT — see [LICENSE](LICENSE).
