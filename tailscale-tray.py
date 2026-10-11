#!/usr/bin/env python3
"""Simple Tailscale tray for Linux desktops supporting StatusNotifier."""
APP_VERSION = "10.0.1"
import json
import os
import re
import getpass
import shutil
import subprocess
import sys
from PyQt6.QtCore import QTimer, QProcess, QUrl
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QDesktopServices
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon


def language():
    # KDE/Qt may expose a preferred UI language separately from LANG.
    for key in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(key, "").strip()
        if value:
            first = value.split(":", 1)[0].split(".", 1)[0].split("@", 1)[0]
            return "de" if first.lower().split("_", 1)[0] == "de" else "en"
    return "en"


LANGUAGE = language()


def tr(de, en):
    return de if LANGUAGE == "de" else en


def run(*args):
    try:
        return subprocess.run(["tailscale", *args], text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 1, "", str(exc))


def question_dialog(parent, title, message, buttons, default_button):
    """Localize only buttons owned by our application's Qt confirmation dialogs."""
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Question)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setStandardButtons(buttons)
    dialog.setDefaultButton(default_button)
    translations = {
        QMessageBox.StandardButton.Yes: tr("Ja", "Yes"),
        QMessageBox.StandardButton.No: tr("Nein", "No"),
        QMessageBox.StandardButton.Cancel: tr("Abbrechen", "Cancel"),
        QMessageBox.StandardButton.Close: tr("Schließen", "Close"),
        QMessageBox.StandardButton.Retry: tr("Wiederholen", "Retry"),
        QMessageBox.StandardButton.Ok: "OK",
    }
    for button_type, label in translations.items():
        button = dialog.button(button_type)
        if button is not None:
            button.setText(label)
    return QMessageBox.StandardButton(dialog.exec())


class TailscaleTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.menu = QMenu()
        self.status_action = QAction(tr('Status wird geprüft …', 'Checking status …'))
        self.status_action.setEnabled(False)
        self.connect_action = QAction(tr('Tailscale verbinden', 'Connect Tailscale'))
        self.disconnect_action = QAction(tr('Tailscale trennen', 'Disconnect Tailscale'))
        self.routes_action = QAction(tr('Subnetz-Routen akzeptieren', 'Accept subnet routes'))
        self.routes_action.setCheckable(True)
        self.routes_action.triggered.connect(self.toggle_routes)
        self.exit_menu = QMenu("Exit Node")
        self.exit_menu.aboutToShow.connect(self.refresh_exit_menu)
        self.show_status_action = QAction(tr('Tailscale-Status anzeigen', 'Show Tailscale status'))
        self.quit_action = QAction(tr('Tray beenden', 'Quit tray'))
        self.connect_action.triggered.connect(self.connect_vpn)
        self.disconnect_action.triggered.connect(self.disconnect_vpn)
        self.show_status_action.triggered.connect(self.show_status)
        self.quit_action.triggered.connect(QApplication.quit)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.connect_action)
        self.menu.addAction(self.disconnect_action)
        self.menu.addSeparator()
        self.menu.addAction(self.routes_action)
        self.menu.addMenu(self.exit_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.show_status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.setContextMenu(self.menu)
        self.activated.connect(self.clicked)
        self.login_process = None
        self.login_output = ""
        self.login_url = None
        self.login_dialog_shown = False
        self.menu.aboutToShow.connect(self.refresh_settings)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)
        self.update_status()
        self.show()

    @staticmethod
    def status_icon(state):
        colors = {"Running": "#22c55e", "NeedsLogin": "#9ca3af"}
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(colors.get(state, "#ef4444")))
        painter.setPen(QColor("#ffffff"))
        painter.drawEllipse(3, 3, 26, 26)
        painter.end()
        return QIcon(pixmap)

    def backend_state(self):
        result = run("status", "--json")
        if result.returncode != 0 and not result.stdout:
            return "Unknown"
        try:
            return json.loads(result.stdout).get("BackendState", "Unknown")
        except (ValueError, TypeError):
            return "Unknown"

    def is_connected(self):
        return self.backend_state() == "Running"

    def update_status(self):
        state = self.backend_state()
        labels = {"Running": tr('Verbunden', 'Connected'), "NeedsLogin": tr('Nicht angemeldet', 'Not signed in'),
                  "Stopped": tr('Getrennt', 'Disconnected'), "Starting": tr('Wird gestartet', 'Starting')}
        label = labels.get(state, tr('Status unbekannt', 'Status unknown'))
        self.setIcon(self.status_icon(state))
        self.setToolTip("Tailscale – " + label)
        self.status_action.setText("● Tailscale: " + label)
        busy = self.login_process is not None
        self.connect_action.setText(tr('Tailscale einrichten / anmelden', 'Set up / sign in to Tailscale') if state == "NeedsLogin" else tr('Tailscale verbinden', 'Connect Tailscale'))
        self.connect_action.setEnabled(state != "Running" and not busy)
        self.disconnect_action.setEnabled(state == "Running" and not busy)

    def status_data(self):
        result = run("status", "--json")
        if not result.stdout:
            return {}
        try:
            return json.loads(result.stdout)
        except (ValueError, TypeError):
            return {}

    def prefs_data(self):
        result = run("debug", "prefs")
        if result.returncode != 0:
            return {}
        try:
            return json.loads(result.stdout)
        except (ValueError, TypeError):
            return {}

    def refresh_settings(self):
        prefs = self.prefs_data()
        route_all = prefs.get("RouteAll")
        self.routes_action.blockSignals(True)
        self.routes_action.setChecked(route_all is True)
        self.routes_action.setEnabled(isinstance(route_all, bool))
        self.routes_action.setToolTip(
            "" if isinstance(route_all, bool)
            else tr('Einstellung konnte nicht ausgelesen werden', 'Could not read setting')
        )
        self.routes_action.blockSignals(False)

    def apply_setting(self, *args):
        result = run("set", *args)
        if result.returncode != 0 and self.permission_denied(result):
            if self.authorize_operator():
                result = run("set", *args)
            else:
                return False
        if result.returncode != 0:
            QMessageBox.warning(
                None, tr('Tailscale – Einstellungen', 'Tailscale – Settings'),
                result.stderr or result.stdout or tr('Einstellung fehlgeschlagen', 'Failed to change setting')
            )
            return False
        self.update_status()
        return True

    def toggle_routes(self, checked):
        self.apply_setting("--accept-routes=" + ("true" if checked else "false"))
        self.refresh_settings()

    def refresh_exit_menu(self):
        self.exit_menu.clear()
        data = self.status_data()
        prefs = self.prefs_data()
        if not data or not prefs:
            action = self.exit_menu.addAction(tr('Exit Nodes nicht verfügbar', 'Exit nodes unavailable'))
            action.setEnabled(False)
            return

        selected_id = prefs.get("ExitNodeID", "")
        # ExitNodeStatus is a fallback for older/newer preference layouts.
        if not selected_id and isinstance(data.get("ExitNodeStatus"), dict):
            selected_id = data["ExitNodeStatus"].get("ID", "")
        no_exit = self.exit_menu.addAction(tr('Keinen Exit Node verwenden', 'Do not use an exit node'))
        no_exit.setCheckable(True)
        no_exit.setChecked(not bool(selected_id))
        no_exit.triggered.connect(lambda _=False: self.select_exit_node(""))

        peers = list((data.get("Peer") or {}).values())
        self_node = data.get("Self")
        if isinstance(self_node, dict):
            peers.append(self_node)
        eligible = [
            peer for peer in peers
            if isinstance(peer, dict) and peer.get("ExitNodeOption") and peer.get("ID")
        ]
        if eligible:
            self.exit_menu.addSeparator()
        for peer in sorted(eligible, key=lambda item: item.get("HostName", "").lower()):
            node_id = peer["ID"]
            name = peer.get("HostName") or peer.get("DNSName") or node_id
            action = self.exit_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(str(selected_id) == str(node_id))
            action.triggered.connect(
                lambda _checked=False, chosen=node_id: self.select_exit_node(chosen)
            )
        if not eligible:
            self.exit_menu.addSeparator()
            action = self.exit_menu.addAction(tr('Keine Exit Nodes verfügbar', 'No exit nodes available'))
            action.setEnabled(False)

    def select_exit_node(self, node_id):
        self.apply_setting("--exit-node=" + str(node_id))
        self.refresh_exit_menu()

    @staticmethod
    def permission_denied(result):
        message = (result.stderr or "") + "\n" + (result.stdout or "")
        message = message.lower()
        return "access denied" in message or "accessdenied" in message or "permission denied" in message

    def authorize_operator(self):
        if not shutil.which("pkexec"):
            QMessageBox.warning(
                None, tr('Tailscale – Berechtigung', 'Tailscale – Permissions'),
                tr('Die Polkit-Anwendung pkexec fehlt.\n', 'The Polkit application pkexec is missing.\n')
                + tr('Bitte einmal im Terminal ausführen:\nsudo tailscale set --operator="$USER"', 'Run this once in a terminal:\nsudo tailscale set --operator="$USER"')
            )
            return False
        username = getpass.getuser()
        answer = question_dialog(
            None, tr('Tailscale – Berechtigung', 'Tailscale – Permissions'),
            tr('Dein Benutzer darf die Tailscale-Verbindung noch nicht steuern.\n\n', 'Your user cannot control the Tailscale connection yet.\n\n')
            + tr('Soll einmalig eine Administratorfreigabe über den Systemdialog ', 'Request one-time administrator authorization through the system dialog ')
            + tr('angefordert werden?\n\n', '?\n\n')
            + tr(f"Der Benutzer {username} wird als Tailscale-Operator eingerichtet.", f"User {username} will be configured as a Tailscale operator."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        try:
            result = subprocess.run(
                ["pkexec", "/usr/bin/tailscale", "set", f"--operator={username}"],
                text=True, capture_output=True, timeout=120
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            QMessageBox.warning(None, tr('Tailscale – Berechtigung', 'Tailscale – Permissions'), str(exc))
            return False
        if result.returncode != 0:
            QMessageBox.warning(
                None, tr('Tailscale – Berechtigung', 'Tailscale – Permissions'),
                tr('Administratorfreigabe fehlgeschlagen oder abgebrochen.\n\n', 'Administrator authorization failed or was canceled.\n\n')
                + (result.stderr or result.stdout or tr('Keine Details verfügbar.', 'No details available.'))
            )
            return False
        return True

    def change_connection(self, command):
        result = run(command)
        if result.returncode != 0 and self.permission_denied(result):
            if self.authorize_operator():
                result = run(command)
            else:
                self.update_status()
                return
        if result.returncode != 0:
            QMessageBox.warning(
                None, "Tailscale",
                result.stderr or result.stdout or tr('Aktion fehlgeschlagen', 'Action failed')
            )
        self.update_status()

    def connect_vpn(self):
        if self.backend_state() == "NeedsLogin":
            self.start_login()
        else:
            self.change_connection("up")
            if self.backend_state() == "NeedsLogin":
                self.start_login()

    def disconnect_vpn(self):
        self.change_connection("down")

    def start_login(self):
        if self.login_process is not None:
            return
        answer = question_dialog(
            None, tr('Tailscale – Ersteinrichtung', 'Tailscale – Initial setup'),
            tr('Dieser Rechner ist noch nicht bei Tailscale angemeldet.\n\n', 'This computer is not signed in to Tailscale yet.\n\n')
            + tr('Soll die Anmeldung gestartet werden? Ein Link wird im Browser geöffnet.', 'Start sign-in? A link will open in your browser.'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.login_output = ""
        self.login_url = None
        self.login_dialog_shown = False
        proc = QProcess(self)
        self.login_process = proc
        proc.setProgram(shutil.which("tailscale") or "/usr/bin/tailscale")
        proc.setArguments(["up"])
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self.login_read_output)
        proc.finished.connect(self.login_finished)
        proc.errorOccurred.connect(self.login_error)
        proc.start()
        self.update_status()

    def login_read_output(self):
        if self.login_process is None:
            return
        chunk = bytes(self.login_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.login_output = (self.login_output + chunk)[-16000:]
        if self.login_url:
            return
        # Only open a Tailscale-owned HTTPS authentication link.
        match = re.search(r"https://login\.tailscale\.com/[A-Za-z0-9_/?=&%.-]+", self.login_output)
        if match:
            self.login_url = match.group(0).rstrip(".,;)")
            QDesktopServices.openUrl(QUrl(self.login_url))
            self.login_dialog_shown = True
            QMessageBox.information(
                None, tr('Tailscale – Anmeldung', 'Tailscale – Sign-in'),
                tr('Der Anmeldelink wurde im Browser geöffnet.\n\n', 'The sign-in link was opened in your browser.\n\n')
                + tr('Bitte melde dich dort bei deinem Tailscale-Account an.\n\n', 'Please sign in to your Tailscale account there.\n\n')
                + tr('Falls sich der Browser nicht öffnet, kopiere diesen Link:\n', 'If the browser does not open, copy this link:\n') + self.login_url
            )

    def login_finished(self, code, _status):
        self.login_read_output()
        self.login_process = None
        self.update_status()
        if self.backend_state() == "Running":
            QMessageBox.information(None, "Tailscale", tr('Anmeldung erfolgreich – Tailscale ist verbunden.', 'Sign-in successful – Tailscale is connected.'))
        elif self.permission_denied(subprocess.CompletedProcess([], code, self.login_output, "")):
            if self.authorize_operator():
                self.start_login()
        else:
            QMessageBox.warning(None, tr('Tailscale – Anmeldung', 'Tailscale – Sign-in'),
                                tr('Die Anmeldung wurde nicht abgeschlossen.\n\n', 'Sign-in was not completed.\n\n') + self.login_output[-2000:])

    def login_error(self, _error):
        if self.login_process is not None and self.login_process.state() == QProcess.ProcessState.NotRunning:
            self.login_read_output()
            self.login_process = None
            self.update_status()
            QMessageBox.warning(None, "Tailscale", tr('Der Anmeldeprozess konnte nicht gestartet werden.', 'Could not start the sign-in process.'))

    def show_status(self):
        result = run("status")
        QMessageBox.information(None, tr('Tailscale-Status', 'Tailscale status'), result.stdout or result.stderr or tr('Kein Status verfügbar', 'No status available'))

    def clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.is_connected():
                self.disconnect_vpn()
            else:
                self.connect_vpn()


def main():
    if not shutil.which("tailscale"):
        print(tr('Fehler: Tailscale ist nicht installiert.', 'Error: Tailscale is not installed.'), file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print(tr('Fehler: Kein System-Tray verfügbar.', 'Error: No system tray available.'), file=sys.stderr)
        return 1
    tray = TailscaleTray()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
