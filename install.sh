#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/tailscale-tray"
AUTOSTART_DIR="$HOME/.config/autostart"
PYTHON_BIN=/usr/bin/python3

fail() { printf '\nFEHLER: %s\n' "$*" >&2; exit 1; }
confirm() {
  local answer
  [[ -t 0 ]] || fail 'Interaktive Bestätigung erforderlich. Bitte im Terminal starten.'
  read -r -p "$1 [j/N]: " answer
  case "$answer" in j|J|ja|Ja|JA|y|Y|yes|Yes|YES) return 0;; *) return 1;; esac
}

printf '\n=== Tailscale Tray – KDE-Installation ===\n\n'
[[ "$EUID" -ne 0 ]] || fail 'Nicht mit sudo starten. Der Installer fragt bei Bedarf selbst.'
[[ -f "$SOURCE_DIR/tailscale-tray.py" ]] || fail 'tailscale-tray.py fehlt neben install.sh.'

printf '[1/5] Distribution und KDE Plasma erkennen ...\n'
[[ -r /etc/os-release ]] || fail '/etc/os-release nicht lesbar.'
# shellcheck disable=SC1091
source /etc/os-release
DISTRO="${PRETTY_NAME:-${ID:-unbekannt}}"
case " ${ID:-} ${ID_LIKE:-} " in
  *nobara*|*fedora*) PKG_MANAGER=dnf; QT_PKG=python3-qt6 ;;
  *cachyos*|*arch*) PKG_MANAGER=pacman; QT_PKG=python-pyqt6 ;;
  *) fail "Nicht unterstützte Distribution: $DISTRO (unterstützt: Nobara/Fedora, CachyOS/Arch)." ;;
esac
command -v "$PKG_MANAGER" >/dev/null || fail "Paketmanager $PKG_MANAGER nicht gefunden."
[[ "${XDG_CURRENT_DESKTOP:-}" == *KDE* || "${XDG_CURRENT_DESKTOP:-}" == *Plasma* || "${DESKTOP_SESSION:-}" == *plasma* ]] || fail 'Bitte aus einer KDE-Plasma-Sitzung starten.'
printf '  Distribution: %s | Paketmanager: %s | KDE Plasma: OK\n' "$DISTRO" "$PKG_MANAGER"

printf '[2/5] Abhängigkeiten prüfen ...\n'
missing=()
command -v tailscale >/dev/null 2>&1 || missing+=(tailscale)
[[ -x "$PYTHON_BIN" ]] || missing+=(python3)
if [[ -x "$PYTHON_BIN" ]] && ! "$PYTHON_BIN" -c 'import PyQt6.QtWidgets' >/dev/null 2>&1; then
  missing+=("$QT_PKG")
elif [[ ! -x "$PYTHON_BIN" ]]; then
  missing+=("$QT_PKG")
fi
if ((${#missing[@]})); then
  printf '  Fehlende Abhängigkeiten: %s\n' "${missing[*]}"
  if confirm 'Fehlende Pakete jetzt mit sudo installieren?'; then
    if [[ "$PKG_MANAGER" == dnf ]]; then
      sudo dnf install "${missing[@]}" || fail 'Paketinstallation fehlgeschlagen. Prüfe Paketquellen und Paketnamen.'
    else
      sudo pacman -S --needed "${missing[@]}" || fail 'Paketinstallation fehlgeschlagen.'
    fi
  else
    fail 'Abgebrochen: Abhängigkeiten fehlen. Keine Dateien installiert.'
  fi
else
  printf '  Alle Abhängigkeiten vorhanden.\n'
fi
command -v tailscale >/dev/null || fail 'tailscale ist weiterhin nicht verfügbar.'
[[ -x "$PYTHON_BIN" ]] || fail 'System-Python fehlt weiterhin.'
"$PYTHON_BIN" -c 'import PyQt6.QtWidgets' >/dev/null 2>&1 || fail 'PyQt6 ist weiterhin nicht mit System-Python nutzbar.'

printf '[3/5] Tailscale-Dienst prüfen ...\n'
if systemctl is-active --quiet tailscaled; then
  printf '  tailscaled läuft.\n'
else
  printf '  tailscaled läuft nicht.\n'
  if confirm 'Tailscale-Dienst jetzt mit sudo aktivieren und starten?'; then
    sudo systemctl enable --now tailscaled || fail 'tailscaled konnte nicht gestartet werden.'
  else
    printf '  Übersprungen. Das Tray funktioniert erst, wenn tailscaled läuft.\n'
  fi
fi

printf '[4/5] Tray installieren ...\n'
mkdir -p -- "$APP_DIR"
install -m 755 -- "$SOURCE_DIR/tailscale-tray.py" "$APP_DIR/tailscale-tray.py"
printf '  %s/tailscale-tray.py\n' "$APP_DIR"

printf '[5/5] KDE-Autostart einrichten ...\n'
mkdir -p -- "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/tailscale-tray.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Tailscale Tray
Comment=Tailscale VPN status and controls
Exec=$PYTHON_BIN $APP_DIR/tailscale-tray.py
Icon=network-vpn
Terminal=false
X-KDE-autostart-after=panel
DESKTOP
chmod 644 -- "$AUTOSTART_DIR/tailscale-tray.desktop"
printf '  %s/tailscale-tray.desktop\n' "$AUTOSTART_DIR"

printf '\n✓ Installation erfolgreich. Tray startet bei der nächsten KDE-Anmeldung.\n'
printf 'Manueller Test: %q %q\n' "$PYTHON_BIN" "$APP_DIR/tailscale-tray.py"
printf 'Bestehende ältere Tray-Installationen wurden nicht geändert oder beendet.\n'
