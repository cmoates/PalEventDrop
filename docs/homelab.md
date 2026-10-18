# Homelab note

PalEventDrop notifications are delivered from your **gaming PC** to **Discord** (channel webhook). No homelab service is required.

If you use [Infisical](https://infisical.com/) on the PC, store `DISCORD_WEBHOOK_URL` there (e.g. path `/palworld`) and run `tools/run-watcher.ps1`. Otherwise use `watcher-config.json` under the event folder — see the main [README](../README.md).
