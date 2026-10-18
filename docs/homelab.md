# Homelab: Apprise `palworld` route

Changes live in `~/homelab-gitops` on host `code`.

## Gitops

`kubernetes/infrastructure/matrix/apprise-deployment.yaml`:

- Init container writes `/keys/palworld.cfg` (Matrix URL, same room as `media` unless you change it).
- Main container mounts `/config/palworld.cfg`.
- External URL: `https://apprise.moat.es/notify/palworld` (ingress `apprise-notify`, no Authelia).

## Secrets (Infisical)

Watcher on the gaming PC uses existing **`/matrix/APPRISE_API_KEY`** (Bearer token). No new secret required unless you create a dedicated key in Infisical and restrict Apprise.

## Apply

After pushing gitops:

```bash
ssh code "cd ~/homelab-gitops && kubectl apply -f kubernetes/infrastructure/matrix/apprise-deployment.yaml"
# or rely on Flux reconciliation
```

Restart Apprise pod if init config does not refresh:

```bash
ssh code "kubectl rollout restart deployment/apprise -n matrix"
```
