# Tailscale Tray für KDE Plasma (v5)

Kleines Python/PyQt6-Tray für Tailscale mit Verbindungsstatus, Verbinden/Trennen und Statusanzeige.

## Unterstützte Systeme
- Nobara / Fedora mit KDE Plasma (`dnf`)
- CachyOS / Arch mit KDE Plasma (`pacman`)

Linux Mint / Cinnamon ist derzeit nicht unterstützt.

## Installation und Updates

```bash
bash install.sh
```

**Nicht mit `sudo` starten.** Der Installer prüft Abhängigkeiten und fragt vor der Installation fehlender Systempakete bzw. dem Start des Tailscale-Dienstes. Die Installation des Trays erfolgt im Benutzerprofil.

Bei Updates erkennt der Installer ausschließlich die neutrale Tailscale-Tray-Installation unter `~/.local/share/tailscale-tray/` und ihren KDE-Autostart unter `~/.config/autostart/tailscale-tray.desktop`. Er fragt vor Updates, sichert vorhandene Dateien in `~/.local/share/tailscale-tray-backups/`, beendet erkannte eigene Tray-Instanzen kontrolliert und bietet den Neustart an.

**v5 enthält keine Erkennung oder Migration früherer individuell benannter Trays.** Solche Autostarts müssen bei Bedarf separat manuell deaktiviert werden.

Bei Installationsfehlern werden die gesicherten Dateien zurückgespielt. Zuvor beendete Tray-Prozesse werden dabei nicht automatisch neu gestartet. Änderungen an Systempaketen oder am Tailscale-Dienst werden nicht zurückgenommen.

## Teststatus

Die v4-Migration wurde auf Nobara 44 erfolgreich ausgeführt. Die v5-Update-Routine ist noch nicht praktisch getestet, ebenso CachyOS. Der Installer wurde auf Bash-Syntax und das Python-Skript auf Syntax geprüft.
