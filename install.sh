#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/tailscale-tray"
AUTOSTART_DIR="$HOME/.config/autostart"
PYTHON_BIN=""

fail() {
  printf '\nFEHLER: %s\n' "$1" >&2
  exit 1
}

printf '\n=== Tailscale Tray – Installation ===\n\n'

printf '[1/5] Benutzer und Quelldateien prüfen ... '
[[ "$EUID" -ne 0 ]] || fail 'Bitte als normaler Benutzer ausführen, nicht mit sudo.'
[[ -f "$SCRIPT_DIR/tailscale-tray.py" ]] || fail 'tailscale-tray.py fehlt im Ordner des Installers.'
printf 'OK\n'

printf '[2/5] Tailscale prüfen ... '
command -v tailscale >/dev/null 2>&1 || fail 'Tailscale fehlt. Bitte zuerst Tailscale installieren und einrichten.'
printf 'OK\n'

printf '[3/5] Python 3 und PyQt6 prüfen ... '
PYTHON_BIN="$(command -v python3 || true)"
[[ -n "$PYTHON_BIN" ]] || fail 'Python 3 fehlt.'
"$PYTHON_BIN" -c 'import PyQt6.QtWidgets' >/dev/null 2>&1 || fail 'PyQt6 fehlt. Auf Nobara ggf.: sudo dnf install python3-qt6'
printf 'OK\n'

printf '[4/5] Programmdatei installieren ... '
mkdir -p -- "$APP_DIR" || fail 'Programmordner konnte nicht erstellt werden.'
install -m 755 -- "$SCRIPT_DIR/tailscale-tray.py" "$APP_DIR/tailscale-tray.py" || fail 'Programmdatei konnte nicht kopiert werden.'
printf 'OK\n'

printf '[5/5] KDE-Autostart einrichten ... '
mkdir -p -- "$AUTOSTART_DIR" || fail 'Autostart-Ordner konnte nicht erstellt werden.'
DESKTOP_FILE="$AUTOSTART_DIR/tailscale-tray.desktop"
cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Tailscale Tray
Comment=Tailscale VPN status and controls
Exec=$PYTHON_BIN $APP_DIR/tailscale-tray.py
Icon=network-vpn
Terminal=false
X-KDE-autostart-after=panel
DESKTOP
chmod 644 -- "$DESKTOP_FILE" || fail 'Autostart-Datei konnte nicht eingerichtet werden.'
printf 'OK\n'

printf '\nInstallation erfolgreich!\n'
printf 'Programm: %s/tailscale-tray.py\n' "$APP_DIR"
printf 'Autostart: %s\n' "$DESKTOP_FILE"
printf 'Das Tray startet bei der nächsten Anmeldung.\n'
printf 'Manueller Test: %s %s/tailscale-tray.py\n' "$PYTHON_BIN" "$APP_DIR"
printf 'Ein bereits laufendes älteres Tray wird nicht beendet.\n'
