# Tailscale Tray for Nobara Linux

Kleines PyQt6-System-Tray zum Verbinden/Trennen von Tailscale, mit Statusanzeige und grünem/rotem Symbol.

## Voraussetzungen

- Nobara Linux mit KDE Plasma und funktionierendem System-Tray
- Python 3 mit PyQt6 (`sudo dnf install python3-qt6`, falls nicht vorhanden)
- Bereits installiertes und eingerichtetes Tailscale (`tailscale` im PATH)

## Installation

Repository herunterladen oder klonen, dann im Repository-Ordner:

```bash
bash install.sh
```

Der Installer prüft Voraussetzungen und installiert ausschließlich im Benutzerprofil:

- `~/.local/share/tailscale-tray/tailscale-tray.py`
- `~/.config/autostart/tailscale-tray.desktop`

Er verändert weder Tailscale-Konfiguration noch bestehende andere Tray-Installationen. Er startet das neue Tray nicht automatisch während der Installation; nach der nächsten Anmeldung startet es per KDE-Autostart. Zum Testen:

```bash
python3 ~/.local/share/tailscale-tray/tailscale-tray.py
```

**Hinweis:** Linksklick verbindet oder trennt Tailscale sofort. Rechtsklick öffnet das Menü. Ein bereits laufendes anderes Tray sollte vor dem Testen beendet werden, damit es nicht zwei Symbole gibt.

## Datenschutz

Keine Zugangsdaten im Repository hinterlegen. Tailscale-Authentifizierung erfolgt über die installierte Tailscale-CLI.
