# PalMaildir architecture

## Idea

Split **transport** from **producers**:

| Layer | Mod | Responsibility |
|-------|-----|----------------|
| Bus | **PalMaildir** | `_G.PalMaildir.publish(event)` → one file under `new/` |
| Producer | **ExpeditionNotifier** (example) | Game hooks → publish typed events |
| Consumer | **palmail-watcher.py** (on PC) | Scan `new/`, notify Apprise, move to `proc/` |

Other authors ship their own producer mods (treasure, base raid, egg hatch) without copying file I/O.

## Maildir layout

```
%LOCALAPPDATA%\Pal\Saved\PalMaildir\
  new\       ← Lua writers only (atomic tmp → rename)
  proc\      ← watcher moves here after successful delivery
  failed\    ← optional; watcher moves here on HTTP errors
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

Load **PalMaildir before** producer mods in `mods.txt`.

```lua
local bus = _G.PalMaildir
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

- Poll `new/*.json` (exclude `*.tmp`).
- Sort by filename (time-ordered prefix).
- POST notification; on success move to `proc/`.
- Idempotent: skip if `id` already in watcher state.

## Why maildir-style drops

Independent files under `new/` mean multiple producer mods can write without coordination. The game side only does atomic create/rename; the OS-side watcher lists and moves files after delivery.
