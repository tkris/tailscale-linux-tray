# Tailscale Linux Tray

**🇩🇪 [Deutsch](#deutsch) | 🇬🇧 [English](#english)**

---

## Deutsch

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

---

## English

A lightweight **Tailscale system tray for Linux with KDE Plasma**. Control Tailscale directly from your desktop panel, including connection status, subnet routes, and exit-node selection.

**Current development version:** v8 · **Application UI language:** German

## Supported systems

| Distribution | Desktop | Package manager | Status |
| --- | --- | --- | --- |
| Nobara Linux | KDE Plasma | `dnf` | Installation and tray tested |
| CachyOS | KDE Plasma | `pacman` | Installation and tray tested |

Other distributions and Linux Mint Cinnamon are not officially supported yet.

## Features

- **Tray status:** Green when connected, red when disconnected, and gray when login is required.
- **Connect and disconnect:** From the context menu or by clicking the tray icon.
- **Initial setup:** Browser-based login to a Tailscale account.
- **Permissions:** If access is denied, the tray can ask for consent and request a one-time administrator authorization through KDE Polkit to configure the current user as a Tailscale operator.
- **Accept subnet routes:** Context-menu checkbox; changes take effect via `tailscale set --accept-routes=true|false`.
- **Select an exit node:** Available exit nodes are discovered dynamically. You can also disable exit-node usage.
- **View status:** Display Tailscale status from the tray.
- **Autostart:** Start the tray automatically with the KDE session.
- **Updates and backups:** The installer updates existing tray installations and backs up installed files.
- **Uninstallation:** Dedicated script with optional deletion of backups.

**Note:** Accepting subnet routes allows the client to use routes advertised by other devices; it does **not** turn your device into a subnet router. Selecting an exit node does not make your device an exit node either.

## Installation

### Clone the repository

```bash
git clone https://github.com/tkris/tailscale-linux-tray.git
cd tailscale-linux-tray
bash install.sh
```

If the repository is private, you need a GitHub account with access to it.

Alternatively, download the repository as a ZIP file from GitHub, extract it, and run `bash install.sh` inside the extracted folder.

**Run the installer as your regular user, not with `sudo bash install.sh`.** It will ask for administrator privileges separately when required.

The installer checks the distribution, KDE Plasma, dependencies, and the `tailscaled` service. Missing packages are installed only after your confirmation. It then offers to launch the tray.

## Updating

If you cloned the repository:

```bash
cd tailscale-linux-tray
git pull
bash install.sh
```

`git pull` updates the project files only. Running `bash install.sh` applies the update to the installed tray.

## Usage

The right-click menu includes:

- Connect or disconnect Tailscale
- Enable or disable **Accept subnet routes**
- Choose an available device under **Exit Node**, or select **Do not use an exit node**
- Show Tailscale status
- Quit the tray

The subnet-route checkbox reflects the current Tailscale preference. Available exit nodes are read from `tailscale status --json`. An exit node must already be advertised and approved in your tailnet.

**Caution:** Selecting an exit node can change the route of your internet traffic. The setting for local LAN access while using an exit node is not changed automatically.

## Uninstallation

From the project directory:

```bash
bash uninstall.sh
```

Run the uninstaller **without `sudo`**. It asks for confirmation before stopping the installed tray and removing:

- `~/.local/share/tailscale-tray/tailscale-tray.py`
- `~/.config/autostart/tailscale-tray.desktop`
- The application directory, if empty afterwards

**Backups:** If `~/.local/share/tailscale-tray-backups/` exists, the script asks **separately** whether to permanently delete the backup directory. The default answer, **No**, keeps the backups.

**Not removed:** The Tailscale package, `tailscaled`, Tailscale login, network settings, and the local Git repository.

## Requirements and notes

- KDE Plasma with working system tray support
- Python 3 and PyQt6
- Tailscale and its `tailscaled` service
- For graphical administrator authentication: `pkexec` and a working Polkit agent

After a kernel update, `tailscaled` may fail if the system is still running the previous kernel. Check the service status and logs first; the tray does not repair the system-level Tailscale installation.

## Project files

```text
tailscale-linux-tray/
├── README.md
├── install.sh
├── uninstall.sh
├── tailscale-tray.py
└── autostart/
    └── tailscale-tray.desktop
```

## Project status

Installation and core tray functions have been tested on Nobara KDE and CachyOS KDE. Some workflows, particularly different exit-node setups and first-time login on additional systems, still need more testing before a general stable release.

---

*Tailscale Linux Tray is an independent community project and is not an official Tailscale product.*
