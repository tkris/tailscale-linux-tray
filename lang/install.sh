#!/usr/bin/env bash
set -Eeuo pipefail


SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$HOME/.local/share/tailscale-tray"
AUTOSTART_DIR="$HOME/.config/autostart"
NEW_PY="$APP_DIR/tailscale-tray.py"
NEW_DESKTOP="$AUTOSTART_DIR/tailscale-tray.desktop"
PYTHON_BIN=/usr/bin/python3
BACKUP_DIR=""
CHANGES_STARTED=0
COMMITTED=0
NEW_PIDS=()

fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
confirm() {
  local answer
  [[ -t 0 ]] || fail 'Confirmation requires an interactive terminal.'
  read -r -p "$1 [y/N]: " answer || return 1
  case "$answer" in j|J|ja|Ja|JA|y|Y|yes|Yes|YES) return 0;; *) return 1;; esac
}

# Match only a Python interpreter executing this exact tray script as its first argument.
# A coincidental script path in another program's command line must never trigger a kill.
is_tray_pid() {
  local pid="$1" target="$2" exe script
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  [[ "$(stat -c %u "/proc/$pid" 2>/dev/null || true)" == "$EUID" ]] || return 1
  local -a argv=()
  mapfile -d '' -t argv < "/proc/$pid/cmdline" || return 1
  ((${#argv[@]} >= 2)) || return 1
  exe="${argv[0]}"; script="${argv[1]}"
  case "${exe##*/}" in python|python[0-9]|python[0-9].[0-9]|python[0-9].[0-9][0-9]) ;; *) return 1 ;; esac
  [[ "$script" == "$target" ]]
}
find_tray_pids() {
  local target="$1" proc pid
  FOUND_PIDS=()
  for proc in /proc/[0-9]*/cmdline; do
    pid="${proc#/proc/}"; pid="${pid%/cmdline}"
    if is_tray_pid "$pid" "$target"; then FOUND_PIDS+=("$pid"); fi
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
    printf '\nInstallation failed: restoring previous files ...\n' >&2
    restore_file "$NEW_PY" new/tailscale-tray.py
    restore_file "$NEW_DESKTOP" new/tailscale-tray.desktop
    printf 'Files restored. Restart previously stopped tray processes manually if needed.\n' >&2
  fi
  exit "$code"
}
trap rollback ERR INT TERM EXIT

printf '\n=== Tailscale Tray v10.2.0 – Linux Installer / Updater ===\n\n'
[[ "$EUID" -ne 0 ]] || fail 'Do not run with sudo.'
[[ -f "$SOURCE_DIR/tailscale-tray.py" ]] || fail 'tailscale-tray.py is missing.'
[[ -f "$SOURCE_DIR/autostart/tailscale-tray.desktop" ]] || fail 'Autostart template is missing.'

printf '[1/7] Checking distribution and desktop ...\n'
# shellcheck disable=SC1091
source /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
  *nobara*|*fedora*) PKG_MANAGER=dnf; QT_PKG=python3-qt6 ;;
  *cachyos*|*arch*) PKG_MANAGER=pacman; QT_PKG=python-pyqt6 ;;
  *linuxmint*|*ubuntu*|*debian*) PKG_MANAGER=apt; QT_PKG=python3-pyqt6 ;;
  *) fail "Unsupported distribution: ${PRETTY_NAME:-unknown}" ;;
esac
if [[ "$PKG_MANAGER" == apt ]]; then
  if [[ "${VERSION_CODENAME:-}" == virginia || "${VERSION_CODENAME:-}" == vera ||
        "${VERSION_CODENAME:-}" == vanessa || "${UBUNTU_CODENAME:-}" == jammy ]]; then
    QT_PKG=python3-pyqt5
  fi
fi
command -v "$PKG_MANAGER" >/dev/null || fail "Package manager $PKG_MANAGER is missing."
DESKTOP_NAME=""
if [[ "${XDG_CURRENT_DESKTOP:-}" == *KDE* || "${XDG_CURRENT_DESKTOP:-}" == *Plasma* || "${DESKTOP_SESSION:-}" == *plasma* ]]; then
  DESKTOP_NAME="KDE Plasma"
elif [[ "${XDG_CURRENT_DESKTOP:-}" == *Cinnamon* || "${DESKTOP_SESSION:-}" == *cinnamon* ]]; then
  DESKTOP_NAME="Cinnamon"
elif [[ "${XDG_CURRENT_DESKTOP:-}" == *[Xx][Ff][Cc][Ee]* || "${DESKTOP_SESSION:-}" == *[Xx][Ff][Cc][Ee]* ]]; then
  DESKTOP_NAME="Xfce"
fi
[[ -n "$DESKTOP_NAME" ]] || fail 'KDE Plasma, Cinnamon or Xfce is required.'
printf '  %s / %s / %s ✓\n' "${PRETTY_NAME:-$ID}" "$PKG_MANAGER" "$DESKTOP_NAME"

printf '[2/7] Checking dependencies ...\n'
missing=()
command -v tailscale >/dev/null 2>&1 || missing+=(tailscale)
[[ -x "$PYTHON_BIN" ]] || missing+=(python3)
if [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c 'import PyQt6.QtWidgets' >/dev/null 2>&1; then
  QT_FOUND=PyQt6
elif [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c 'import PyQt5.QtWidgets' >/dev/null 2>&1; then
  QT_FOUND=PyQt5
else
  QT_FOUND=""
  missing+=("$QT_PKG")
fi
if ((${#missing[@]})); then
  printf '  Missing: %s\n' "${missing[*]}"
  if confirm 'Install missing packages?'; then
    case "$PKG_MANAGER" in
      dnf) sudo dnf install "${missing[@]}" ;;
      pacman) sudo pacman -S --needed "${missing[@]}" ;;
      apt) sudo apt-get update && sudo apt-get install "${missing[@]}" ;;
    esac
  else fail 'Canceled; no application files changed.'; fi
else printf '  All dependencies available ✓\n'; fi
command -v tailscale >/dev/null || fail 'tailscale is still missing.'
[[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c 'import PyQt6.QtWidgets' >/dev/null 2>&1 ||
  { [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c 'import PyQt5.QtWidgets' >/dev/null 2>&1; } || fail 'Python/PyQt5 or PyQt6 not ready.'
"$PYTHON_BIN" -m py_compile "$SOURCE_DIR/tailscale-tray.py" || fail 'Python syntax error.'

printf '[3/7] Checking Tailscale service ...\n'
if systemctl is-active --quiet tailscaled; then printf '  tailscaled is running ✓\n';
elif confirm 'tailscaled is inactive. Enable and start it?'; then
  sudo systemctl enable --now tailscaled || fail 'Could not start tailscaled. Check journalctl -u tailscaled -b.'
  systemctl is-active --quiet tailscaled || fail 'tailscaled is not running after start attempt. Check journalctl -u tailscaled -b.';
else printf '  Service unchanged; the tray needs tailscaled running.\n'; fi

# Check boot-time activation independently of whether the service is running.
if systemctl is-enabled --quiet tailscaled; then
  printf '  tailscaled autostart enabled ✓\n'
elif confirm 'tailscaled is not enabled to start at boot. Enable autostart?'; then
  sudo systemctl enable tailscaled || fail 'Could not enable tailscaled autostart.'
  systemctl is-enabled --quiet tailscaled || fail 'tailscaled autostart is still not enabled.'
  printf '  tailscaled autostart enabled ✓\n'
else
  printf '  Autostart unchanged; tailscaled may not start automatically after reboot.\n'
fi


printf '[4/7] Checking existing installation and processes ...\n'
if [[ -f "$NEW_PY" ]]; then
  printf '  Existing installation: %s\n' "$NEW_PY"
  current_version="$(sed -nE 's/^APP_VERSION = "([^"]+)"/\1/p' "$NEW_PY" | head -n 1)"
  printf '  Detected version: %s\n' "${current_version:-unknown (older version)}"
fi
[[ -f "$NEW_DESKTOP" ]] && printf '  Existing autostart: %s\n' "$NEW_DESKTOP"
find_tray_pids "$NEW_PY"; NEW_PIDS=("${FOUND_PIDS[@]}")
printf '  Running Tailscale tray instances: %s\n' "${#NEW_PIDS[@]}"

if [[ -f "$NEW_PY" || -f "$NEW_DESKTOP" || ${#NEW_PIDS[@]} -gt 0 ]]; then
  confirm 'Update the existing Tailscale tray and restart if needed?' || fail 'Update canceled.'
fi

printf '[5/7] Backing up and stopping old tray instances ...\n'
BACKUP_DIR="$HOME/.local/share/tailscale-tray-backups/$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p -- "$BACKUP_DIR"
backup_file "$NEW_PY" new/tailscale-tray.py
backup_file "$NEW_DESKTOP" new/tailscale-tray.desktop
printf '  Backup: %s\n' "$BACKUP_DIR"
CHANGES_STARTED=1
pids=("${NEW_PIDS[@]}")
if ((${#pids[@]})); then
  for pid in "${pids[@]}"; do
    [[ -r "/proc/$pid/cmdline" ]] || continue
    if is_tray_pid "$pid" "$NEW_PY"; then
      kill -TERM -- "$pid" 2>/dev/null || true
    fi
  done
  for _ in 1 2 3 4 5; do
    alive=0
    for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    ((alive == 0)) && break
    sleep 1
  done
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then fail "Tray process $pid did not stop. SIGKILL was not sent."; fi
  done
fi

printf '[6/7] Installing tray and autostart ...\n'
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
DESKTOP
chmod 644 -- "$NEW_DESKTOP"
printf '  Files and autostart updated ✓\n'

printf '[7/7] Starting new tray ...\n'
if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  if confirm 'Start the new Tailscale tray now?'; then
    "$PYTHON_BIN" "$NEW_PY" >"$BACKUP_DIR/tray-start.log" 2>&1 &
    new_pid=$!
    sleep 2
    if kill -0 "$new_pid" 2>/dev/null; then
      printf '  Started (PID %s) ✓\n' "$new_pid"
    else
      fail "Tray failed to start. Log: $BACKUP_DIR/tray-start.log"
    fi
  else printf '  Not started; autostart will run at next login.\n'; fi
else printf '  No graphical session detected; autostart will run at next login.\n'; fi
COMMITTED=1
printf '\n✓ Installation/update successful!\nBackup: %s\n' "$BACKUP_DIR"
printf '  Only this user’s Tailscale tray installation was updated.\n'
