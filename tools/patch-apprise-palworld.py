#!/usr/bin/env python3
"""Patch homelab Apprise deployment to add palworld notify key."""
from pathlib import Path

path = Path.home() / "homelab-gitops/kubernetes/infrastructure/matrix/apprise-deployment.yaml"
text = path.read_text()

old = (
    "              printf 'matrix://:%s@synapse.matrix.svc.cluster.local:8008/!RVsFIEFRsSEVrgqESn:moat.es&e2ee=no\\n' \"$APPRISE_MATRIX_TOKEN\" > /keys/matrix-monitoring.cfg\n"
    "              chmod 600 /keys/media.cfg /keys/matrix-monitoring.cfg"
)
new = (
    "              printf 'matrix://:%s@synapse.matrix.svc.cluster.local:8008/!RVsFIEFRsSEVrgqESn:moat.es&e2ee=no\\n' \"$APPRISE_MATRIX_TOKEN\" > /keys/matrix-monitoring.cfg\n"
    "              printf 'matrix://:%s@synapse.matrix.svc.cluster.local:8008/!RVsFIEFRsSEVrgqESn:moat.es?image=yes&e2ee=no\\n' \"$APPRISE_MATRIX_TOKEN\" > /keys/palworld.cfg\n"
    "              chmod 600 /keys/media.cfg /keys/matrix-monitoring.cfg /keys/palworld.cfg"
)
if old not in text:
    raise SystemExit("init block not found")
text = text.replace(old, new, 1)

old2 = (
    "            - name: apprise-keys\n"
    "              mountPath: /config/matrix-monitoring.cfg\n"
    "              subPath: matrix-monitoring.cfg\n"
    "              readOnly: true\n"
    "            - name: cache"
)
new2 = (
    "            - name: apprise-keys\n"
    "              mountPath: /config/matrix-monitoring.cfg\n"
    "              subPath: matrix-monitoring.cfg\n"
    "              readOnly: true\n"
    "            - name: apprise-keys\n"
    "              mountPath: /config/palworld.cfg\n"
    "              subPath: palworld.cfg\n"
    "              readOnly: true\n"
    "            - name: cache"
)
if old2 not in text:
    raise SystemExit("mount block not found")
text = text.replace(old2, new2, 1)

path.write_text(text)
print("patched", path)

cm = Path.home() / "homelab-gitops/kubernetes/infrastructure/matrix/configmaps.yaml"
cm_text = cm.read_text()
needle = "  # matrix-monitoring -> Alertmanager webhook"
if "# palworld -> PalMaildir watcher" not in cm_text:
    cm_text = cm_text.replace(
        needle,
        "  # palworld -> PalMaildir watcher (gaming PC)\n" + needle,
        1,
    )
    cm.write_text(cm_text)
    print("patched", cm)
