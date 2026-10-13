#!/usr/bin/env python3
"""Simple Tailscale tray for Linux desktops supporting StatusNotifier."""
APP_VERSION = "10.1.0"
import json
import os
import re
import getpass
import shutil
import subprocess
import sys
try:
    from PyQt6.QtCore import QTimer, QProcess, QUrl
    from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QDesktopServices
    from PyQt6.QtWidgets import (QApplication, QMenu, QMessageBox, QSystemTrayIcon,
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
        QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton)
    QT_VERSION = 6
except ImportError as exc:
    # Fall back only when PyQt6 itself is missing, not when its installation is broken.
    if not (exc.name == 'PyQt6' or (exc.name or '').startswith('PyQt6.')):
        raise
    from PyQt5.QtCore import QTimer, QProcess, QUrl
    from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QDesktopServices
    from PyQt5.QtWidgets import (QAction, QApplication, QMenu, QMessageBox,
        QSystemTrayIcon, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton)
    QT_VERSION = 5

# Qt5 and Qt6 expose these enums in different places.
MSG_BUTTON = QMessageBox.StandardButton if QT_VERSION == 6 else QMessageBox
MSG_ICON = QMessageBox.Icon if QT_VERSION == 6 else QMessageBox
TRAY_REASON = QSystemTrayIcon.ActivationReason if QT_VERSION == 6 else QSystemTrayIcon
PROC_CHANNEL = QProcess.ProcessChannelMode if QT_VERSION == 6 else QProcess
PROC_STATE = QProcess.ProcessState if QT_VERSION == 6 else QProcess
PAINTER_HINT = QPainter.RenderHint if QT_VERSION == 6 else QPainter
TABLE_EDIT = QAbstractItemView.EditTrigger if QT_VERSION == 6 else QAbstractItemView
TABLE_SELECT = QAbstractItemView.SelectionBehavior if QT_VERSION == 6 else QAbstractItemView
HEADER_MODE = QHeaderView.ResizeMode if QT_VERSION == 6 else QHeaderView



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
    dialog.setIcon(MSG_ICON.Question)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setStandardButtons(buttons)
    dialog.setDefaultButton(default_button)
    translations = {
        MSG_BUTTON.Yes: tr("Ja", "Yes"),
        MSG_BUTTON.No: tr("Nein", "No"),
        MSG_BUTTON.Cancel: tr("Abbrechen", "Cancel"),
        MSG_BUTTON.Close: tr("Schließen", "Close"),
        MSG_BUTTON.Retry: tr("Wiederholen", "Retry"),
        MSG_BUTTON.Ok: "OK",
    }
    for button_type, label in translations.items():
        button = dialog.button(button_type)
        if button is not None:
            button.setText(label)
    return MSG_BUTTON(dialog.exec()) if QT_VERSION == 6 else dialog.exec_()


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
        self.current_state = "Unknown"
        self.status_process = None
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
        painter.setRenderHint(PAINTER_HINT.Antialiasing)
        painter.setBrush(QColor(colors.get(state, "#ef4444")))
        painter.setPen(QColor("#ffffff"))
        painter.drawEllipse(3, 3, 26, 26)
        painter.end()
        return QIcon(pixmap)

    def backend_state(self):
        return self.current_state

    def is_connected(self):
        return self.current_state == "Running"

    def update_status(self):
        """Poll without blocking the Qt event loop or overlapping requests."""
        if self.status_process is not None:
            return
        proc = QProcess(self)
        self.status_process = proc
        proc.setProgram(shutil.which("tailscale") or "/usr/bin/tailscale")
        proc.setArguments(["status", "--json"])
        proc.finished.connect(lambda code, status, process=proc: self.status_finished(process, code))
        proc.errorOccurred.connect(lambda error, process=proc: self.status_error(process))
        proc.start()

    def status_error(self, proc):
        if proc is self.status_process and proc.state() == PROC_STATE.NotRunning:
            self.finish_status_process(proc, "Unknown")

    def status_finished(self, proc, code):
        if proc is not self.status_process:
            return
        state = "Unknown"
        if code == 0:
            try:
                data = json.loads(bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace"))
                if isinstance(data, dict) and isinstance(data.get("BackendState"), str):
                    state = data["BackendState"]
            except (ValueError, TypeError):
                pass
        self.finish_status_process(proc, state)

    def finish_status_process(self, proc, state):
        if proc is not self.status_process:
            return
        self.status_process = None
        proc.deleteLater()
        self.current_state = state
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
        if result.returncode != 0 or not result.stdout:
            return {}
        try:
            data = json.loads(result.stdout)
            return data if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            return {}

    def prefs_data(self):
        result = run("debug", "prefs")
        if result.returncode != 0:
            return {}
        try:
            data = json.loads(result.stdout)
            return data if isinstance(data, dict) else {}
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

        peer_data = data.get("Peer")
        peers = list(peer_data.values()) if isinstance(peer_data, dict) else []
        self_node = data.get("Self")
        if isinstance(self_node, dict):
            peers.append(self_node)
        eligible = [
            peer for peer in peers
            if isinstance(peer, dict) and peer.get("ExitNodeOption") and peer.get("ID")
        ]
        if eligible:
            self.exit_menu.addSeparator()
        for peer in sorted(eligible, key=lambda item: str(item.get("HostName") or "").lower()):
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
            MSG_BUTTON.Yes | MSG_BUTTON.No,
            MSG_BUTTON.No
        )
        if answer != MSG_BUTTON.Yes:
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

    def disconnect_vpn(self):
        self.change_connection("down")

    def start_login(self, ask_confirmation=True):
        if self.login_process is not None:
            return
        if ask_confirmation:
            answer = question_dialog(
                None, tr('Tailscale – Ersteinrichtung', 'Tailscale – Initial setup'),
                tr('Dieser Rechner ist noch nicht bei Tailscale angemeldet.\n\n', 'This computer is not signed in to Tailscale yet.\n\n')
                + tr('Soll die Anmeldung gestartet werden? Ein Link wird im Browser geöffnet.', 'Start sign-in? A link will open in your browser.'),
                MSG_BUTTON.Yes | MSG_BUTTON.No,
                MSG_BUTTON.Yes
            )
            if answer != MSG_BUTTON.Yes:
                return
        self.login_output = ""
        self.login_url = None
        self.login_dialog_shown = False
        proc = QProcess(self)
        self.login_process = proc
        proc.setProgram(shutil.which("tailscale") or "/usr/bin/tailscale")
        proc.setArguments(["up"])
        proc.setProcessChannelMode(PROC_CHANNEL.MergedChannels)
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
                self.start_login(ask_confirmation=False)
        else:
            QMessageBox.warning(None, tr('Tailscale – Anmeldung', 'Tailscale – Sign-in'),
                                tr('Die Anmeldung wurde nicht abgeschlossen.\n\n', 'Sign-in was not completed.\n\n') + self.login_output[-2000:])

    def login_error(self, _error):
        if self.login_process is not None and self.login_process.state() == PROC_STATE.NotRunning:
            self.login_read_output()
            self.login_process = None
            self.update_status()
            QMessageBox.warning(None, "Tailscale", tr('Der Anmeldeprozess konnte nicht gestartet werden.', 'Could not start the sign-in process.'))

    def show_status(self):
        data = self.status_data()
        if not data:
            QMessageBox.warning(None, tr('Tailscale-Status', 'Tailscale status'),
                                tr('Status konnte nicht geladen werden.', 'Could not load status.'))
            return

        dialog = QDialog()
        dialog.setWindowTitle(tr('Tailscale – Netzwerkstatus', 'Tailscale – Network status'))
        dialog.resize(850, 440)
        layout = QVBoxLayout(dialog)
        headline = QLabel()
        layout.addWidget(headline)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            tr('Gerät', 'Device'), 'Tailscale-IP', 'OS',
            tr('Status', 'Status'), tr('Verbindung', 'Connection')
        ])
        table.setEditTriggers(TABLE_EDIT.NoEditTriggers)
        table.setSelectionBehavior(TABLE_SELECT.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, HEADER_MODE.Stretch)
        for col in range(1, 5):
            table.horizontalHeader().setSectionResizeMode(col, HEADER_MODE.ResizeToContents)
        layout.addWidget(table)

        buttons = QHBoxLayout()
        buttons.addStretch()
        refresh = QPushButton(tr('Aktualisieren', 'Refresh'))
        close = QPushButton(tr('Schließen', 'Close'))
        buttons.addWidget(refresh)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        close.clicked.connect(dialog.accept)

        def populate():
            current = self.status_data()
            if not current:
                QMessageBox.warning(dialog, tr('Tailscale-Status', 'Tailscale status'),
                                    tr('Status konnte nicht geladen werden.', 'Could not load status.'))
                return
            backend = current.get('BackendState', 'Unknown')
            states = {'Running': tr('Verbunden', 'Connected'),
                      'Stopped': tr('Getrennt', 'Disconnected'),
                      'NeedsLogin': tr('Nicht angemeldet', 'Not signed in'),
                      'Starting': tr('Wird gestartet', 'Starting')}
            devices = []
            own = current.get('Self')
            if isinstance(own, dict):
                devices.append((own, True))
            peers = current.get('Peer') or {}
            if isinstance(peers, dict):
                devices.extend((peer, False) for peer in peers.values() if isinstance(peer, dict))
            headline.setText('Tailscale: ' + states.get(backend, str(backend)) +
                             '   |   ' + tr('Geräte: ', 'Devices: ') + str(len(devices)))
            table.setRowCount(len(devices))
            for row, (device, is_self) in enumerate(devices):
                name = device.get('HostName') or device.get('DNSName') or '?'
                if is_self:
                    name += tr(' (dieses Gerät)', ' (this device)')
                ips = device.get('TailscaleIPs') or []
                ip = ips[0] if ips else '–'
                online = is_self or bool(device.get('Online'))
                status = (tr('Dieses Gerät', 'This device') if is_self else
                          tr('Online', 'Online') if online else tr('Offline', 'Offline'))
                if is_self:
                    connection = '–'
                elif not online:
                    connection = '–'
                elif device.get('CurAddr'):
                    connection = tr('Direkt', 'Direct')
                elif device.get('Relay'):
                    connection = 'Relay (' + str(device['Relay']) + ')'
                else:
                    connection = '–'
                values = [name, ip, device.get('OS') or '–', status, connection]
                for col, value in enumerate(values):
                    table.setItem(row, col, QTableWidgetItem(str(value)))

        refresh.clicked.connect(populate)
        populate()
        dialog.exec() if QT_VERSION == 6 else dialog.exec_()

    def clicked(self, reason):
        if reason == TRAY_REASON.Trigger:
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
    return app.exec() if QT_VERSION == 6 else app.exec_()


if __name__ == "__main__":
    sys.exit(main())
