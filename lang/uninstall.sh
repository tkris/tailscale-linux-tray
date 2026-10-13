#!/usr/bin/env bash
set -Eeuo pipefail


APP_DIR="$HOME/.local/share/tailscale-tray"
APP_FILE="$APP_DIR/tailscale-tray.py"
AUTOSTART_FILE="$HOME/.config/autostart/tailscale-tray.desktop"
BACKUP_DIR="$HOME/.local/share/tailscale-tray-backups"

confirm() {
  local reply
  [[ -t 0 ]] || { printf 'An interactive terminal is required.\n' >&2; return 1; }
  read -r -p "$1 [y/N]: " reply || return 1
  case "$reply" in j|J|ja|Ja|JA|y|Y|yes|Yes|YES) return 0;; *) return 1;; esac
}

[[ "$EUID" -ne 0 ]] || { echo 'Please run without sudo.' >&2; exit 1; }
printf '\n=== Tailscale Tray – Uninstallation ===\n\n'
printf 'The following installed files will be removed (if present):\n  %s\n  %s\n' "$APP_FILE" "$AUTOSTART_FILE"
printf '\nTailscale itself and tailscaled will remain installed.\n\n'
if ! confirm 'Really uninstall Tailscale Tray?'; then
  echo 'Canceled. No changes made.'
  exit 0
fi

# Only stop this user's process if its argv contains the exact installed script path.
pids=()
for proc in /proc/[0-9]*/cmdline; do
  [[ -r "$proc" ]] || continue
  pid="${proc#/proc/}"; pid="${pid%/cmdline}"
  [[ "$(stat -c %u "/proc/$pid" 2>/dev/null || true)" == "$EUID" ]] || continue
  while IFS= read -r -d '' arg; do
    if [[ "$arg" == "$APP_FILE" ]]; then pids+=("$pid"); break; fi
  done < "$proc" || true
done

if ((${#pids[@]})); then
  printf 'Stopping %s running tray instance(s) ...\n' "${#pids[@]}"
  for pid in "${pids[@]}"; do
    if [[ -r "/proc/$pid/cmdline" ]] && tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq -- "$APP_FILE"; then
      kill -TERM -- "$pid" 2>/dev/null || true
    fi
  done
  for _ in 1 2 3 4 5; do
    remaining=0
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then remaining=1; fi
    done
    ((remaining == 0)) && break
    sleep 1
  done
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      printf 'Tray process %s is still running. Stop it manually; no files were deleted.\n' "$pid" >&2
      exit 1
    fi
  done
fi

rm -f -- "$APP_FILE" "$AUTOSTART_FILE"
# Remove the application's directory only if it is empty; leave unrelated files untouched.
rmdir -- "$APP_DIR" 2>/dev/null || true
printf 'Tray and KDE autostart removed.\n'

if [[ -d "$BACKUP_DIR" ]]; then
  printf '\nBackups found: %s\n' "$BACKUP_DIR"
  if confirm 'Permanently delete all backups of this tray application?'; then
    rm -rf -- "$BACKUP_DIR"
    echo 'Backups deleted.'
  else
    echo 'Backups kept.'
  fi
else
  echo 'No Tailscale tray backups found.'
fi

printf '\n✓ Uninstallation complete. Tailscale itself was not modified.\n'
