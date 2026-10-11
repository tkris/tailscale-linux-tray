# Tailscale Tray für KDE Plasma

Ein einfaches Tailscale-System-Tray mit PyQt6 für **Nobara/Fedora** und **CachyOS/Arch Linux** mit KDE Plasma.

## Installation

Tailscale muss anschließend noch für den jeweiligen Benutzer angemeldet werden (`tailscale up`), falls das noch nicht erfolgt ist.

1. Repository als ZIP herunterladen und entpacken oder mit Git klonen.
2. Terminal im Projektordner öffnen.
3. `bash install.sh` ausführen (nicht mit `sudo`).

Der Installer erkennt die Distribution anhand von `/etc/os-release`, prüft KDE Plasma, Python 3, PyQt6 und Tailscale und fragt **vor** jeder Installation fehlender Pakete um Erlaubnis. Falls `tailscaled` nicht läuft, fragt er separat, ob er den Dienst mit `sudo systemctl enable --now tailscaled` aktivieren soll. Ohne Zustimmung werden keine Pakete installiert und kein Dienst gestartet.

Die Anwendung wird nach `~/.local/share/tailscale-tray/` installiert, der Autostart nach `~/.config/autostart/tailscale-tray.desktop`. Das Tray startet beim nächsten KDE-Login. Es wird kein laufendes Tray beendet.

**Hinweis:** Ein älteres Tray mit einem anderen Namen kann parallel starten. Vor einem produktiven Wechsel den alten Autostart separat deaktivieren. Die Installation wurde syntaktisch geprüft, aber noch nicht auf beiden Distributionen praktisch getestet. Bei distributionsabhängigen Paketquellen kann eine Paketinstallation fehlschlagen; der Installer meldet das dann.

## Bedienung

- Grün: Tailscale läuft; Rot: getrennt oder nicht verfügbar
- Linksklick: verbinden/trennen
- Rechtsklick: Status und Aktionen

## Sicherheit

Das Skript enthält keine fest hinterlegten Zugangsdaten. Der Installer fordert nur für Paketinstallation oder Dienstaktivierung `sudo` an.
