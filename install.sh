#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/tailscale-tray"
AUTOSTART_DIR="$HOME/.config/autostart"
NEW_PY="$APP_DIR/tailscale-tray.py"
NEW_DESKTOP="$AUTOSTART_DIR/tailscale-tray.desktop"
OLD_PY="$HOME/.local/share/skynet-vpn/skynet-vpn.py"
OLD_DESKTOP="$AUTOSTART_DIR/skynet-vpn.desktop"
PYTHON_BIN=/usr/bin/python3
BACKUP_DIR=""
CHANGES_STARTED=0
COMMITTED=0
OLD_PIDS=()
NEW_PIDS=()

fail() { printf '\nFEHLER: %s\n' "$*" >&2; exit 1; }
confirm() {
  local answer
  [[ -t 0 ]] || fail 'Bestätigung nur in einem interaktiven Terminal möglich.'
  read -r -p "$1 [j/N]: " answer || return 1
  case "$answer" in j|J|ja|Ja|JA|y|Y|yes|Yes|YES) return 0;; *) return 1;; esac
}

# Only match this user's exact known Python script paths, not tailscaled or other trays.
find_tray_pids() {
  local target="$1" proc pid arg matched
  FOUND_PIDS=()
  for proc in /proc/[0-9]*/cmdline; do
    [[ -r "$proc" ]] || continue
    pid="${proc#/proc/}"; pid="${pid%/cmdline}"
    [[ "$(stat -c %u "/proc/$pid" 2>/dev/null || true)" == "$EUID" ]] || continue
    matched=0
    while IFS= read -r -d '' arg; do
      if [[ "$arg" == "$target" ]]; then matched=1; fi
    done < "$proc" || true
    ((matched)) && FOUND_PIDS+=("$pid")
  done
}

backup_file() {
  local file="$1" relative="$2"
  if [[ -f "$file" ]]; then
    mkdir -p -- "$BACKUP_DIR/$(dirname "$relative")"
    cp -p -- "$file" "$BACKUP_DIR/$relative"
  fi
}
restore_file() {
  local file="$1" relative="$2"
  if [[ -f "$BACKUP_DIR/$relative" ]]; then
    mkdir -p -- "$(dirname "$file")"
    cp -p -- "$BACKUP_DIR/$relative" "$file"
  else
    rm -f -- "$file"
  fi
}
rollback() {
  local code=$?
  trap - ERR INT TERM EXIT
  if ((CHANGES_STARTED && !COMMITTED)); then
    printf '\nInstallation fehlgeschlagen: bisherige Dateien werden wiederhergestellt ...\n' >&2
    restore_file "$NEW_PY" new/tailscale-tray.py
    restore_file "$NEW_DESKTOP" new/tailscale-tray.desktop
    restore_file "$OLD_PY" old/skynet-vpn.py
    restore_file "$OLD_DESKTOP" old/skynet-vpn.desktop
    printf 'Dateien wiederhergestellt. Zuvor beendete Tray-Prozesse bitte ggf. manuell neu starten.\n' >&2
  fi
  exit "$code"
}
trap rollback ERR INT TERM EXIT

printf '\n=== Tailscale Tray v4 – KDE Installer / Updater ===\n\n'
[[ "$EUID" -ne 0 ]] || fail 'Nicht mit sudo ausführen.'
[[ -f "$SOURCE_DIR/tailscale-tray.py" ]] || fail 'tailscale-tray.py fehlt.'
[[ -f "$SOURCE_DIR/autostart/tailscale-tray.desktop" ]] || fail 'Autostart-Vorlage fehlt.'

printf '[1/7] Distribution und KDE prüfen ...\n'
# shellcheck disable=SC1091
source /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
  *nobara*|*fedora*) PKG_MANAGER=dnf; QT_PKG=python3-qt6 ;;
  *cachyos*|*arch*) PKG_MANAGER=pacman; QT_PKG=python-pyqt6 ;;
  *) fail "Distribution nicht unterstützt: ${PRETTY_NAME:-unbekannt}" ;;
esac
command -v "$PKG_MANAGER" >/dev/null || fail "Paketmanager $PKG_MANAGER fehlt."
[[ "${XDG_CURRENT_DESKTOP:-}" == *KDE* || "${XDG_CURRENT_DESKTOP:-}" == *Plasma* || "${DESKTOP_SESSION:-}" == *plasma* ]] || fail 'KDE Plasma ist erforderlich.'
printf '  %s / %s / KDE Plasma ✓\n' "${PRETTY_NAME:-$ID}" "$PKG_MANAGER"

printf '[2/7] Abhängigkeiten prüfen ...\n'
missing=()
command -v tailscale >/dev/null 2>&1 || missing+=(tailscale)
[[ -x "$PYTHON_BIN" ]] || missing+=(python3)
if [[ ! -x "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c 'import PyQt6.QtWidgets' >/dev/null 2>&1; then missing+=("$QT_PKG"); fi
if ((${#missing[@]})); then
  printf '  Fehlend: %s\n' "${missing[*]}"
  if confirm 'Fehlende Pakete installieren?'; then
    if [[ "$PKG_MANAGER" == dnf ]]; then sudo dnf install "${missing[@]}"; else sudo pacman -S --needed "${missing[@]}"; fi
  else fail 'Abgebrochen; keine Anwendungsdateien verändert.'; fi
else printf '  Alle vorhanden ✓\n'; fi
command -v tailscale >/dev/null || fail 'tailscale fehlt weiterhin.'
[[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c 'import PyQt6.QtWidgets' || fail 'Python/PyQt6 nicht einsatzbereit.'
"$PYTHON_BIN" -m py_compile "$SOURCE_DIR/tailscale-tray.py" || fail 'Python-Syntaxfehler.'

printf '[3/7] Tailscale-Dienst prüfen ...\n'
if systemctl is-active --quiet tailscaled; then printf '  tailscaled läuft ✓\n';
elif confirm 'tailscaled ist inaktiv. Aktivieren und starten?'; then sudo systemctl enable --now tailscaled;
else printf '  Dienst unverändert; Tray benötigt einen laufenden tailscaled.\n'; fi

printf '[4/7] Bestehende Installation und Prozesse suchen ...\n'
if [[ -f "$NEW_PY" ]]; then
  printf '  Neue Installation vorhanden: %s\n' "$NEW_PY"
  current_version="$(sed -nE 's/^APP_VERSION = "([^"]+)"/\1/p' "$NEW_PY" | head -n 1)"
  printf '  Erkannte Version: %s\n' "${current_version:-unbekannt (ältere Version)}"
fi
[[ -f "$NEW_DESKTOP" ]] && printf '  Neuer Autostart vorhanden: %s\n' "$NEW_DESKTOP"
[[ -f "$OLD_PY" ]] && printf '  SKYNET-Altversion vorhanden: %s\n' "$OLD_PY"
[[ -f "$OLD_DESKTOP" ]] && printf '  SKYNET-Autostart vorhanden: %s\n' "$OLD_DESKTOP"
find_tray_pids "$NEW_PY"; NEW_PIDS=("${FOUND_PIDS[@]}")
find_tray_pids "$OLD_PY"; OLD_PIDS=("${FOUND_PIDS[@]}")
printf '  Laufende neue Instanzen: %s | SKYNET-Instanzen: %s\n' "${#NEW_PIDS[@]}" "${#OLD_PIDS[@]}"

MIGRATE=0
if [[ -f "$OLD_PY" || -f "$OLD_DESKTOP" || ${#OLD_PIDS[@]} -gt 0 ]]; then
  if confirm 'Alte SKYNET-Version sichern, beenden und Autostart entfernen?'; then MIGRATE=1;
  else
    printf '  SKYNET bleibt unverändert.\n'
    if [[ -f "$OLD_DESKTOP" || ${#OLD_PIDS[@]} -gt 0 ]]; then
      fail 'Abbruch: Zwei parallel laufende Trays/Autostarts werden vermieden.'
    fi
  fi
fi
if [[ -f "$NEW_PY" || -f "$NEW_DESKTOP" || ${#NEW_PIDS[@]} -gt 0 ]]; then
  confirm 'Bestehendes Tailscale Tray aktualisieren und ggf. neu starten?' || fail 'Update abgebrochen.'
fi

printf '[5/7] Sicherung erstellen und alte Tray-Instanzen beenden ...\n'
BACKUP_DIR="$HOME/.local/share/tailscale-tray-backups/$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p -- "$BACKUP_DIR"
backup_file "$NEW_PY" new/tailscale-tray.py
backup_file "$NEW_DESKTOP" new/tailscale-tray.desktop
if ((MIGRATE)); then
  backup_file "$OLD_PY" old/skynet-vpn.py
  backup_file "$OLD_DESKTOP" old/skynet-vpn.desktop
fi
printf '  Backup: %s\n' "$BACKUP_DIR"
CHANGES_STARTED=1
pids=("${NEW_PIDS[@]}")
if ((MIGRATE)); then pids+=("${OLD_PIDS[@]}"); fi
if ((${#pids[@]})); then
  kill -TERM -- "${pids[@]}" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    alive=0
    for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    ((alive == 0)) && break
    sleep 1
  done
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then fail "Tray-Prozess $pid beendet sich nicht. Kein SIGKILL gesendet."; fi
  done
fi

printf '[6/7] Tray und KDE-Autostart installieren ...\n'
mkdir -p -- "$APP_DIR" "$AUTOSTART_DIR"
install -m 755 -- "$SOURCE_DIR/tailscale-tray.py" "$NEW_PY"
cat > "$NEW_DESKTOP" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Tailscale Tray
Comment=Tailscale VPN status and controls
Exec=$PYTHON_BIN $NEW_PY
Icon=network-vpn
Terminal=false
X-KDE-autostart-after=panel
DESKTOP
chmod 644 -- "$NEW_DESKTOP"
if ((MIGRATE)); then
  rm -f -- "$OLD_DESKTOP"
  # Keep the old Python file as a local fallback; only disable its autostart.
fi
printf '  Dateien und Autostart aktualisiert ✓\n'

printf '[7/7] Neues Tray starten ...\n'
if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  if confirm 'Neues Tailscale Tray jetzt starten?'; then
    "$PYTHON_BIN" "$NEW_PY" >"$BACKUP_DIR/tray-start.log" 2>&1 &
    new_pid=$!
    sleep 2
    if kill -0 "$new_pid" 2>/dev/null; then
      printf '  Gestartet (PID %s) ✓\n' "$new_pid"
    else
      fail "Tray startet nicht. Log: $BACKUP_DIR/tray-start.log"
    fi
  else printf '  Nicht gestartet; Autostart beim nächsten Login aktiv.\n'; fi
else printf '  Keine grafische Sitzung erkannt; Autostart beim nächsten Login aktiv.\n'; fi
COMMITTED=1
printf '\n✓ Installation/Update erfolgreich!\nBackup: %s\n' "$BACKUP_DIR"
printf '  SKYNET-Python-Datei wurde nicht gelöscht. Der alte Autostart wurde nur bei bestätigter Migration entfernt.\n'
