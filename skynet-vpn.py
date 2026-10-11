#!/usr/bin/env python3

import subprocess
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon


def run(*args):
    return subprocess.run(
        ["tailscale", *args],
        text=True,
        capture_output=True
    )


class SkynetTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()

        self.menu = QMenu()

        self.status_action = QAction("Status wird geprüft …")
        self.status_action.setEnabled(False)

        self.connect_action = QAction("SKYNET verbinden")
        self.disconnect_action = QAction("SKYNET trennen")
        self.show_status_action = QAction("Tailscale-Status anzeigen")
        self.quit_action = QAction("Tray beenden")

        self.connect_action.triggered.connect(self.connect_vpn)
        self.disconnect_action.triggered.connect(self.disconnect_vpn)
        self.show_status_action.triggered.connect(self.show_status)
        self.quit_action.triggered.connect(QApplication.quit)

        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.connect_action)
        self.menu.addAction(self.disconnect_action)
        self.menu.addSeparator()
        self.menu.addAction(self.show_status_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)
        self.activated.connect(self.clicked)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)

        self.update_status()
        self.show()

    def status_icon(self, connected):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#22c55e" if connected else "#ef4444"))
        painter.setPen(QColor("#ffffff"))
        painter.drawEllipse(3, 3, 26, 26)
        painter.end()

        return QIcon(pixmap)

    def is_connected(self):
        result = run("status", "--json")
        return result.returncode == 0 and '"BackendState": "Running"' in result.stdout

    def update_status(self):
        connected = self.is_connected()

        if connected:
            self.setIcon(self.status_icon(True))
            self.setToolTip("SKYNET VPN – verbunden")
            self.status_action.setText("● SKYNET VPN: Verbunden")
            self.connect_action.setEnabled(False)
            self.disconnect_action.setEnabled(True)
        else:
            self.setIcon(self.status_icon(False))
            self.setToolTip("SKYNET VPN – getrennt")
            self.status_action.setText("○ SKYNET VPN: Getrennt")
            self.connect_action.setEnabled(True)
            self.disconnect_action.setEnabled(False)

    def connect_vpn(self):
        result = run("up")
        if result.returncode != 0:
            QMessageBox.warning(None, "SKYNET VPN", result.stderr)
        self.update_status()

    def disconnect_vpn(self):
        result = run("down")
        if result.returncode != 0:
            QMessageBox.warning(None, "SKYNET VPN", result.stderr)
        self.update_status()

    def show_status(self):
        result = run("status")
        text = result.stdout or result.stderr
        QMessageBox.information(None, "Tailscale Status", text)

    def clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.is_connected():
                self.disconnect_vpn()
            else:
                self.connect_vpn()


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

tray = SkynetTray()

sys.exit(app.exec())
