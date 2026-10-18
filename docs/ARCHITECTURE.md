# PalEventDrop architecture

## Idea

Split **transport** from **producers**:

| Layer | Mod | Responsibility |
|-------|-----|----------------|
| Library | **PalEventDrop** | `_G.PalEventDrop.publish(event)` → one file under `pending/` |
| Producer | **ExpeditionNotifier** (example) | Game hooks → publish typed events |
| Consumer | **event-watcher.py** (on PC) | Scan `pending/`, POST Discord webhook, move to `done/` |

Other authors ship their own producer mods (treasure, base raid, egg hatch) without copying file I/O.

## Folder layout

```
%LOCALAPPDATA%\Pal\Saved\PalEventDrop\
  pending\   ← game mods write here (atomic tmp → rename)
  done\      ← watcher moves here after successful delivery
  failed\    ← watcher moves here on HTTP / parse errors
```

Writers never read directories (UE4SS Lua cannot list dirs reliably). Unique filenames avoid collisions without locking.

## Event envelope (schema 1)

```json
{
  "schema": 1,
  "id": "hex-seq-rand",
  "ts": "2026-10-17T22:00:00Z",
  "source": "ExpeditionNotifier",
  "type": "expedition_complete",
  "title": "Expedition complete",
  "message": "…",
  "payload": { "optional": "strings" }
}
```

## Producer API

Load **PalEventDrop before** producer mods in `mods.txt`.

```lua
local bus = _G.PalEventDrop
if bus then
    bus.publish({
        source = "MyMod",
        type = "my_event",
        title = "Title",
        message = "Body",
        payload = { key = "value" },
    })
end
```

Returns `id, err` from `publish` (pcall-safe; check err).

## Consumer contract

- Poll `pending/*.json` (exclude `*.tmp`).
- Sort by filename (time-ordered prefix).
- POST to Discord webhook (`DISCORD_WEBHOOK_URL` or `watcher-config.json`); on success move to `done/`.
- Idempotent: skip if `id` already in watcher state.

## Why one file per event

Multiple producer mods can write at the same time without sharing a single log file. The game only creates files; the PC-side watcher lists folders and handles delivery.
