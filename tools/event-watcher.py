#!/usr/bin/env python3
"""Poll PalEventDrop pending/ and POST events to a Discord channel webhook."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "Pal" / "Saved" / "PalEventDrop"
DEFAULT_STATE = DEFAULT_ROOT / "watcher-state.json"
DEFAULT_CONFIG_NAME = "watcher-config.json"
POLL_SECONDS = 1.0
MAX_SENT_IDS = 500

# Palworld Steam capsule (Discord thumbnail)
DEFAULT_THUMBNAIL = (
    "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1623730/capsule_231x87.jpg"
)

# event type -> (embed color, title emoji)
TYPE_STYLE: dict[str, tuple[int, str]] = {
    "expedition_complete": (0x3BA55C, "⛺"),
    "test": (0x5865F2, "🧪"),
}
DEFAULT_STYLE = (0xE89540, "🎮")


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def event_dirs(root: Path) -> tuple[Path, Path, Path, Path]:
    return root / "pending", root / "processing", root / "done", root / "failed"


def ensure_dirs(root: Path) -> tuple[Path, Path, Path, Path]:
    pending_dir, processing_dir, done_dir, failed_dir = event_dirs(root)
    for path in (root, pending_dir, processing_dir, done_dir, failed_dir):
        path.mkdir(parents=True, exist_ok=True)
    return pending_dir, processing_dir, done_dir, failed_dir


def config_file_candidates(root: Path) -> list[Path]:
    custom = env("PALEVENTDROP_WATCHER_CONFIG")
    paths: list[Path] = []
    if custom:
        paths.append(Path(custom))
    paths.append(root / DEFAULT_CONFIG_NAME)
    return paths


def load_config_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("config root must be a JSON object")
    return data


def resolve_watcher_config(root: Path) -> tuple[str, str | None, str | None]:
    """Return (discord_webhook_url, optional username, optional avatar_url). Env overrides file."""
    webhook = env("DISCORD_WEBHOOK_URL")
    username = env("DISCORD_WEBHOOK_USERNAME")
    avatar_url = env("DISCORD_WEBHOOK_AVATAR_URL")

    file_data: dict[str, Any] = {}
    config_path: Path | None = None
    for candidate in config_file_candidates(root):
        if candidate.is_file():
            try:
                file_data = load_config_file(candidate)
                config_path = candidate
                break
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise RuntimeError(f"invalid watcher config {candidate}: {exc}") from exc

    if not webhook:
        raw = file_data.get("discord_webhook_url") or file_data.get("webhook_url")
        if isinstance(raw, str) and raw.strip():
            webhook = raw.strip()

    if not username:
        raw = file_data.get("discord_username") or file_data.get("username")
        if isinstance(raw, str) and raw.strip():
            username = raw.strip()

    if not avatar_url:
        raw = file_data.get("discord_avatar_url") or file_data.get("avatar_url")
        if isinstance(raw, str) and raw.strip():
            avatar_url = raw.strip()

    if not webhook:
        paths = ", ".join(str(p) for p in config_file_candidates(root))
        raise RuntimeError(
            "Discord webhook not configured. Set DISCORD_WEBHOOK_URL (Infisical or env) "
            f"or create watcher-config.json with discord_webhook_url. Tried: {paths}"
        )

    if "discord.com/api/webhooks/" not in webhook:
        raise RuntimeError("discord_webhook_url does not look like a Discord webhook URL")

    if config_path and not env("DISCORD_WEBHOOK_URL"):
        print(f"[event-watcher] config={config_path}")

    return webhook, username, avatar_url


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"sent_ids": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sent_ids": []}
    if not isinstance(data.get("sent_ids"), list):
        data["sent_ids"] = []
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def humanize_event_type(event_type: str) -> str:
    event_type = event_type.strip()
    if not event_type:
        return "Event"
    return event_type.replace("_", " ").strip().title()


def normalize_timestamp(ts: Any) -> str | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    ts = ts.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}T", ts):
        return ts if ts.endswith("Z") or "+" in ts else f"{ts}Z"
    return None


def build_embed(event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("type") or "").strip()
    title = str(event.get("title") or humanize_event_type(event_type) or "Palworld")
    message = str(event.get("message") or event.get("type") or title).strip()
    source = str(event.get("source") or "").strip()

    color, emoji = TYPE_STYLE.get(event_type, DEFAULT_STYLE)
    embed: dict[str, Any] = {
        "title": f"{emoji} {title}"[:256],
        "description": message[:4096] if message else "*No details*",
        "color": color,
        "thumbnail": {"url": DEFAULT_THUMBNAIL},
        "footer": {"text": "Palworld · PalEventDrop"},
    }

    ts = normalize_timestamp(event.get("ts"))
    if ts:
        embed["timestamp"] = ts

    if source:
        embed["author"] = {"name": source}

    fields: list[dict[str, Any]] = []
    if event_type:
        fields.append(
            {
                "name": "Type",
                "value": humanize_event_type(event_type)[:256],
                "inline": True,
            }
        )

    payload = event.get("payload")
    if isinstance(payload, dict):
        for key, value in payload.items():
            if not isinstance(key, str):
                continue
            if isinstance(value, (str, int, float, bool)):
                fields.append(
                    {
                        "name": key.replace("_", " ").title()[:256],
                        "value": str(value)[:1024],
                        "inline": True,
                    }
                )
            if len(fields) >= 6:
                break

    if fields:
        embed["fields"] = fields

    return embed


def post_discord(
    webhook_url: str,
    event: dict[str, Any],
    username: str | None,
    avatar_url: str | None,
) -> None:
    body: dict[str, Any] = {"embeds": [build_embed(event)]}
    if username:
        body["username"] = username[:80]
    if avatar_url:
        body["avatar_url"] = avatar_url[:512]

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PalEventDrop-watcher",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def list_json_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files = [
        p
        for p in directory.glob("*.json")
        if p.is_file() and not p.name.endswith(".tmp") and p.stat().st_size > 0
    ]
    return sorted(files, key=lambda p: p.name)


def claim_pending(path: Path, processing_dir: Path) -> Path | None:
    dest = processing_dir / path.name
    try:
        shutil.move(str(path), str(dest))
        return dest
    except OSError:
        return None


def process_file(
    path: Path,
    done_dir: Path,
    failed_dir: Path,
    webhook_url: str,
    username: str | None,
    avatar_url: str | None,
    state: dict,
) -> None:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"[event-watcher] read failed {path.name}: {exc}", file=sys.stderr)
        return

    if not raw.strip():
        return

    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[event-watcher] bad json {path.name}: {exc}", file=sys.stderr)
        dest = failed_dir / path.name
        if path.exists():
            shutil.move(str(path), str(dest))
        return

    if not isinstance(event, dict):
        print(f"[event-watcher] bad json {path.name}: root must be object", file=sys.stderr)
        dest = failed_dir / path.name
        if path.exists():
            shutil.move(str(path), str(dest))
        return

    event_id = str(event.get("id") or "")
    if event_id and event_id in state["sent_ids"]:
        dest = done_dir / path.name
        if path.exists():
            shutil.move(str(path), str(dest))
        return

    try:
        post_discord(webhook_url, event, username, avatar_url)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"[event-watcher] discord failed {path.name}: {exc}", file=sys.stderr)
        dest = failed_dir / path.name
        if path.exists():
            shutil.move(str(path), str(dest))
        return

    if event_id:
        state["sent_ids"].append(event_id)
        if len(state["sent_ids"]) > MAX_SENT_IDS:
            state["sent_ids"] = state["sent_ids"][-MAX_SENT_IDS:]

    dest = done_dir / path.name
    shutil.move(str(path), str(dest))


def poll_once(
    root: Path,
    state_path: Path,
    webhook_url: str,
    username: str | None,
    avatar_url: str | None,
) -> None:
    pending_dir, processing_dir, done_dir, failed_dir = ensure_dirs(root)
    state = load_state(state_path)

    for path in list_json_files(processing_dir):
        try:
            process_file(path, done_dir, failed_dir, webhook_url, username, avatar_url, state)
        except OSError as exc:
            print(f"[event-watcher] io error {path.name}: {exc}", file=sys.stderr)

    for path in list_json_files(pending_dir):
        claimed = claim_pending(path, processing_dir)
        if not claimed:
            continue
        try:
            process_file(claimed, done_dir, failed_dir, webhook_url, username, avatar_url, state)
        except OSError as exc:
            print(f"[event-watcher] io error {claimed.name}: {exc}", file=sys.stderr)

    save_state(state_path, state)


def main() -> int:
    root = Path(env("PALEVENTDROP_ROOT", str(DEFAULT_ROOT)))
    state_path = Path(env("PALEVENTDROP_STATE", str(DEFAULT_STATE)))

    try:
        webhook_url, username, avatar_url = resolve_watcher_config(root)
    except RuntimeError as exc:
        print(f"[event-watcher] {exc}", file=sys.stderr)
        print(
            "Infisical example: infisical run --env=prod --path=/palworld -- python tools/event-watcher.py",
            file=sys.stderr,
        )
        print(
            f"Config example: copy tools/watcher-config.example.json to {root / DEFAULT_CONFIG_NAME}",
            file=sys.stderr,
        )
        return 1

    ensure_dirs(root)
    print(f"[event-watcher] events={root}")
    print("[event-watcher] notify=discord (webhook)")
    print("[event-watcher] run a single watcher process (duplicates = double Discord posts)")

    while True:
        poll_once(root, state_path, webhook_url, username, avatar_url)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
