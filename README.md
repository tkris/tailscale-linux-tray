# Tailscale Tray v8

KDE-Plasma-Tray für Tailscale auf Nobara (dnf) und CachyOS (pacman).

## Neu in v8
- Checkbox **Subnetz-Routen akzeptieren**, synchronisiert mit der echten Tailscale-Einstellung `RouteAll` (`tailscale debug prefs`).
- Untermenü **Exit Node**: `Keinen Exit Node verwenden` oder einen von Tailscale als Exit Node angebotenen Peer auswählen.
- Die Auswahl verwendet `tailscale set --exit-node=<Node-ID>` bzw. `tailscale set --exit-node=`; kein eigener Exit Node wird angeboten.
- Bei fehlenden Rechten bleibt die Einwilligung + KDE-Polkit-Freigabe aus v6 erhalten.
- Einrichtungs-/Browser-Login aus v7 bleibt erhalten.
- Installer ohne SKYNET-Migration, mit Backup und Update-Unterstützung.

## Installation / Update
Entpacken und als normaler Benutzer im Projektordner ausführen:

```bash
bash install.sh
```

## Deinstallation

Die mitgelieferte `uninstall.sh` im Projektordner **als normaler Benutzer (ohne `sudo`)** starten:

```bash
bash uninstall.sh
```

Das Skript fragt zuerst, ob das Tray wirklich deinstalliert werden soll. Nach Bestätigung:

- beendet es laufende Instanzen des installierten Tailscale-Trays;
- entfernt `~/.local/share/tailscale-tray/tailscale-tray.py`;
- entfernt `~/.config/autostart/tailscale-tray.desktop`;
- entfernt das Anwendungsverzeichnis nur, wenn es anschließend leer ist.

**Backups:** Falls `~/.local/share/tailscale-tray-backups/` vorhanden ist, fragt das Skript **gesondert**, ob dieser gesamte Backup-Ordner dauerhaft gelöscht werden soll. Die Standardantwort **N** bewahrt die Backups auf. Das Löschen ist nicht rückgängig zu machen.

**Nicht betroffen:** Das Tailscale-Paket, der Dienst `tailscaled`, die Tailnet-Anmeldung, VPN-Konfiguration und Netzwerkeinstellungen werden nicht entfernt oder verändert. Auch das heruntergeladene Git-Repository beziehungsweise der entpackte Projektordner bleibt erhalten.

## Hinweise
- Die verfügbaren Exit Nodes werden aus `tailscale status --json` gelesen (`Peer[].ExitNodeOption`).
- Die gesetzten Optionen werden aus `tailscale debug prefs` gelesen (`RouteAll`, `ExitNodeID`). Wenn Einstellungen nicht lesbar sind, bleibt die Checkbox deaktiviert bzw. das Exit-Node-Menü zeigt einen Hinweis.
- Ein Exit Node muss im Tailnet bereits bereitgestellt und freigegeben sein.
- Beim Auswählen eines Exit Nodes wird der Internetverkehr über diesen Knoten geleitet. Eine lokale LAN-Freigabe (`--exit-node-allow-lan-access`) wird nicht automatisch verändert.
- Unter KDE muss ein grafischer Polkit-Agent laufen, um Administratorrechte anzufordern.
- v8 wurde unter CachyOS KDE praktisch getestet; einzelne Funktionen sollten vor einem offiziellen Stable-Release weiterhin gesondert geprüft werden.

## Enthalten
`install.sh`, `uninstall.sh`, `tailscale-tray.py`, `autostart/tailscale-tray.desktop`, `README.md`.
