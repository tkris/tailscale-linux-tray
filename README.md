# Tailscale Tray für KDE Plasma (v4)

Ein kleines Python/PyQt6-Tray für Tailscale mit Verbindungsstatus, Verbinden/Trennen und Statusanzeige.

## Unterstützte Systeme
- Nobara / Fedora mit KDE Plasma (`dnf`)
- CachyOS / Arch mit KDE Plasma (`pacman`)

Linux Mint / Cinnamon ist noch nicht getestet und wird derzeit nicht unterstützt.

## Installation

Im entpackten Projektordner ein Terminal öffnen:

```bash
bash install.sh
```

**Nicht mit `sudo` starten.** Fehlende Systempakete und ein inaktiver `tailscaled`-Dienst werden erkannt; vor Systemänderungen wird gefragt. Für die Tray-Installation wird kein Root benötigt.

## Updates und Migration

Der Installer prüft vorhandene `tailscale-tray.py`- und ältere `skynet-vpn.py`-Installationen sowie deren Autostart-Dateien und laufende Prozesse. Er fragt vor einem Update oder der Migration. Er sichert vorhandene Dateien unter `~/.local/share/tailscale-tray-backups/`, beendet nur erkannte Instanzen dieser beiden Skriptpfade und richtet den neuen Autostart ein. Die alte `skynet-vpn.py` bleibt als lokale Rückfallkopie erhalten; bei bestätigter Migration wird nur ihr Autostart entfernt.

Das neue Tray kann auf Wunsch direkt gestartet werden. Der Installer beendet **nicht** den Tailscale-Dienst und verwendet kein `killall` oder `pkill`.

**Hinweis:** Ein Dateifehler führt zur Wiederherstellung der gesicherten Dateien. Bereits beendete Tray-Prozesse werden bei einem Fehler nicht automatisch wieder gestartet. Änderungen an Systempaketen und dem `tailscaled`-Dienst werden nicht rückgängig gemacht.

## Sicherheit und Teststatus

Die Bash- und Python-Syntax wurde geprüft. Ein vollständiger Lauf auf Nobara und CachyOS ist noch erforderlich. Bitte zunächst auf einem Testsystem testen oder die Dateien sichern.

Das Tray ruft `tailscale up`, `tailscale down` und `tailscale status` auf; Tailscale selbst muss installiert und eingerichtet sein.
