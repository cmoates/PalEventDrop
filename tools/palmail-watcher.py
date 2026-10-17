#!/usr/bin/env python3
"""Poll PalMaildir new/ and POST events to Apprise (Matrix)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "Pal" / "Saved" / "PalMaildir"
DEFAULT_STATE = DEFAULT_ROOT / "watcher-state.json"
DEFAULT_URL = "https://apprise.moat.es/notify/palworld"
POLL_SECONDS = 1.0
MAX_SENT_IDS = 500


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def maildir_paths(root: Path) -> tuple[Path, Path, Path]:
    return root / "new", root / "proc", root / "failed"


def ensure_maildir(root: Path) -> tuple[Path, Path, Path]:
    new_dir, proc_dir, failed_dir = maildir_paths(root)
    for path in (root, new_dir, proc_dir, failed_dir):
        path.mkdir(parents=True, exist_ok=True)
    return new_dir, proc_dir, failed_dir


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


def post_apprise(url: str, token: str, title: str, message: str) -> None:
    body = json.dumps({"title": title, "body": message, "format": "text"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def list_pending(new_dir: Path) -> list[Path]:
    if not new_dir.is_dir():
        return []
    files = [
        p
        for p in new_dir.glob("*.json")
        if p.is_file() and not p.name.endswith(".tmp")
    ]
    return sorted(files, key=lambda p: p.name)


def process_file(
    path: Path,
    proc_dir: Path,
    failed_dir: Path,
    url: str,
    token: str,
    state: dict,
) -> None:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[palmail-watcher] bad json {path.name}: {exc}", file=sys.stderr)
        dest = failed_dir / path.name
        shutil.move(str(path), str(dest))
        return

    event_id = str(event.get("id") or "")
    if event_id and event_id in state["sent_ids"]:
        dest = proc_dir / path.name
        if path.exists():
            shutil.move(str(path), str(dest))
        return

    title = str(event.get("title") or "Palworld")
    message = str(event.get("message") or event.get("type") or title)

    try:
        post_apprise(url, token, title, message)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"[palmail-watcher] notify failed {path.name}: {exc}", file=sys.stderr)
        dest = failed_dir / path.name
        if path.exists():
            shutil.move(str(path), str(dest))
        return

    if event_id:
        state["sent_ids"].append(event_id)
        if len(state["sent_ids"]) > MAX_SENT_IDS:
            state["sent_ids"] = state["sent_ids"][-MAX_SENT_IDS:]

    dest = proc_dir / path.name
    shutil.move(str(path), str(dest))


def poll_once(
    root: Path,
    state_path: Path,
    url: str,
    token: str,
) -> None:
    new_dir, proc_dir, failed_dir = ensure_maildir(root)
    state = load_state(state_path)

    for path in list_pending(new_dir):
        try:
            process_file(path, proc_dir, failed_dir, url, token, state)
        except OSError as exc:
            print(f"[palmail-watcher] io error {path.name}: {exc}", file=sys.stderr)

    save_state(state_path, state)


def main() -> int:
    root = Path(env("PALMAILDIR_ROOT", str(DEFAULT_ROOT)))
    state_path = Path(env("PALMAILDIR_STATE", str(DEFAULT_STATE)))
    url = env("APPRISE_NOTIFY_URL", DEFAULT_URL)
    token = env("APPRISE_API_KEY")

    if not token:
        print(
            "Set APPRISE_API_KEY (Infisical: /matrix/APPRISE_API_KEY). "
            "Example: infisical run --env=prod --path=/matrix -- python tools/palmail-watcher.py",
            file=sys.stderr,
        )
        return 1

    ensure_maildir(root)
    print(f"[palmail-watcher] maildir={root}")
    print(f"[palmail-watcher] apprise={url}")

    while True:
        poll_once(root, state_path, url, token)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
