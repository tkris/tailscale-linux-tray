# Tailscale Linux Tray

Ein leichtgewichtiges **Tailscale-System-Tray für Linux mit KDE Plasma**. Es ermöglicht, Tailscale direkt über die Taskleiste zu steuern – einschließlich Verbindungsstatus, Subnetz-Routen und Exit-Node-Auswahl.

**Aktueller Entwicklungsstand:** v8 · **Sprache der Oberfläche:** Deutsch

## Unterstützte Systeme

| Distribution | Desktop | Paketmanager | Stand |
| --- | --- | --- | --- |
| Nobara Linux | KDE Plasma | `dnf` | Installation und Tray getestet |
| CachyOS | KDE Plasma | `pacman` | Installation und Tray getestet |

Weitere Distributionen und Linux Mint Cinnamon sind derzeit nicht offiziell unterstützt.

## Funktionen

- **Tray-Status:** Grün bei bestehender Verbindung, Rot bei getrennter Verbindung und Grau, wenn eine Anmeldung erforderlich ist.
- **Verbinden und Trennen:** Über das Kontextmenü oder per Klick auf das Tray-Symbol.
- **Ersteinrichtung:** Unterstützung für die Anmeldung am Tailscale-Account über den Browser.
- **Berechtigungen:** Bei fehlenden Rechten kann nach Zustimmung eine einmalige Administratorfreigabe über KDE Polkit angefordert und der aktuelle Benutzer als Tailscale-Operator eingerichtet werden.
- **Subnetz-Routen akzeptieren:** Checkbox im Kontextmenü; Änderungen werden direkt über `tailscale set --accept-routes=true|false` angewendet.
- **Exit Node auswählen:** Verfügbare Exit Nodes werden dynamisch aus dem Tailscale-Status gelesen. Die Nutzung kann im Menü auch wieder deaktiviert werden.
- **Status anzeigen:** Tailscale-Status direkt aus dem Tray abrufen.
- **Autostart:** Automatischer Start des Trays mit der KDE-Sitzung.
- **Updates und Backups:** Der Installer kann bestehende Tray-Versionen aktualisieren und zuvor installierte Dateien sichern.
- **Deinstallation:** Separates Skript mit optionaler Löschung der angelegten Backups.

**Hinweis:** Die Option „Subnetz-Routen akzeptieren“ verwendet bereits von anderen Geräten angebotene Routen. Sie richtet **keinen eigenen Subnet-Router** ein. Ebenso wählt die Exit-Node-Funktion einen bestehenden Exit Node aus; sie macht den Laptop nicht selbst zum Exit Node.

## Installation

### Repository klonen

```bash
git clone https://github.com/tkris/tailscale-linux-tray.git
cd tailscale-linux-tray
bash install.sh
```

Das Repository ist gegebenenfalls privat. In diesem Fall benötigst du eine GitHub-Anmeldung und die entsprechende Zugriffsberechtigung.

Alternativ kannst du das Projekt als ZIP von GitHub herunterladen, entpacken und im entpackten Ordner `bash install.sh` ausführen.

**Installer als normaler Benutzer starten – nicht mit `sudo bash install.sh`.** Wenn Systempakete oder Dienste angepasst werden müssen, fragt das Skript gesondert nach Administratorrechten.

Der Installer prüft die Linux-Distribution, KDE Plasma, benötigte Programme und den Dienst `tailscaled`. Fehlende Pakete werden nur nach Zustimmung installiert. Er bietet anschließend an, das Tray zu starten.

## Updates

Wenn du das Repository mit Git geklont hast:

```bash
cd tailscale-linux-tray
git pull
bash install.sh
```

`git pull` aktualisiert zunächst nur die Projektdateien. Erst `bash install.sh` führt das Update der installierten Tray-Anwendung durch.

## Bedienung

Über das Rechtsklickmenü stehen unter anderem diese Funktionen zur Verfügung:

- Tailscale verbinden oder trennen
- **Subnetz-Routen akzeptieren** ein- oder ausschalten
- Unter **Exit Node** einen verfügbaren Exit Node auswählen oder **Keinen Exit Node verwenden** einstellen
- Tailscale-Status anzeigen
- Tray beenden

Die Subnetz-Einstellung wird aus den aktuellen Tailscale-Einstellungen ausgelesen. Exit Nodes werden aus `tailscale status --json` ermittelt. Ein Exit Node muss im Tailnet bereits bereitgestellt und freigegeben sein.

**Achtung:** Die Wahl eines Exit Nodes kann die Route deines Internetverkehrs ändern. Die Einstellung für lokalen LAN-Zugriff bei Exit-Node-Nutzung wird nicht automatisch verändert.

## Deinstallation

Im Projektordner:

```bash
bash uninstall.sh
```

Der Deinstaller wird **ohne `sudo`** gestartet und fragt vor dem Entfernen der Tray-Anwendung nach einer Bestätigung. Er beendet laufende Instanzen des installierten Trays und entfernt:

- `~/.local/share/tailscale-tray/tailscale-tray.py`
- `~/.config/autostart/tailscale-tray.desktop`
- Das Anwendungsverzeichnis, sofern es danach leer ist

**Backups:** Wenn `~/.local/share/tailscale-tray-backups/` vorhanden ist, fragt der Deinstaller **separat**, ob dieser Backup-Ordner dauerhaft gelöscht werden soll. Die Standardantwort **Nein** bewahrt die Backups auf.

**Nicht entfernt werden:** das Tailscale-Paket, `tailscaled`, die Tailscale-Anmeldung, Netzwerkkonfigurationen und das lokale Git-Repository.

## Voraussetzungen und Hinweise

- KDE Plasma mit funktionierender System-Tray-Unterstützung
- Python 3 und PyQt6
- Tailscale und der Dienst `tailscaled`
- Für die grafische Administratorfreigabe: `pkexec` und ein funktionierender Polkit-Agent

Ein Fehler beim Start von `tailscaled` kann beispielsweise nach einem Kernel-Update auftreten, wenn noch der vorherige Kernel läuft. In diesem Fall zuerst den Dienststatus und die Systemlogs prüfen; das Tray ersetzt keine Reparatur der Tailscale-Systeminstallation.

## Projektdateien

```text
tailscale-linux-tray/
├── README.md
├── install.sh
├── uninstall.sh
├── tailscale-tray.py
└── autostart/
    └── tailscale-tray.desktop
```

## Projektstatus

Die Installation und zentrale Tray-Funktionen wurden unter Nobara KDE und CachyOS KDE praktisch ausprobiert. Einzelne Abläufe, insbesondere unterschiedliche Exit-Node-Konfigurationen und die Ersteinrichtung auf weiteren Systemen, sollten vor einem allgemeinen Stable-Release zusätzlich getestet werden.

---

*Tailscale Linux Tray ist ein unabhängiges Community-Projekt und kein offizielles Produkt von Tailscale.*
