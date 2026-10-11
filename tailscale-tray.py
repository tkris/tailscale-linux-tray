#!/usr/bin/env python3
"""Simple Tailscale tray for Linux desktops supporting StatusNotifier."""
import json
import shutil
import subprocess
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon


def run(*args):
    try:
        return subprocess.run(["tailscale", *args], text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 1, "", str(exc))


class TailscaleTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.menu = QMenu()
        self.status_action = QAction("Status wird geprüft …")
        self.status_action.setEnabled(False)
        self.connect_action = QAction("Tailscale verbinden")
        self.disconnect_action = QAction("Tailscale trennen")
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

    @staticmethod
    def status_icon(connected):
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
        if result.returncode != 0:
            return False
        try:
            return json.loads(result.stdout).get("BackendState") == "Running"
        except (ValueError, TypeError):
            return False

    def update_status(self):
        connected = self.is_connected()
        self.setIcon(self.status_icon(connected))
        self.setToolTip("Tailscale – verbunden" if connected else "Tailscale – getrennt")
        self.status_action.setText("● Tailscale: Verbunden" if connected else "○ Tailscale: Getrennt")
        self.connect_action.setEnabled(not connected)
        self.disconnect_action.setEnabled(connected)

    def connect_vpn(self):
        result = run("up")
        if result.returncode != 0:
            QMessageBox.warning(None, "Tailscale", result.stderr or "Verbindung fehlgeschlagen")
        self.update_status()

    def disconnect_vpn(self):
        result = run("down")
        if result.returncode != 0:
            QMessageBox.warning(None, "Tailscale", result.stderr or "Trennen fehlgeschlagen")
        self.update_status()

    def show_status(self):
        result = run("status")
        QMessageBox.information(None, "Tailscale-Status", result.stdout or result.stderr or "Kein Status verfügbar")

    def clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.is_connected():
                self.disconnect_vpn()
            else:
                self.connect_vpn()


def main():
    if not shutil.which("tailscale"):
        print("Fehler: Tailscale ist nicht installiert.", file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("Fehler: Kein System-Tray verfügbar.", file=sys.stderr)
        return 1
    tray = TailscaleTray()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
