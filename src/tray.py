"""A passive system tray indicator for the running application."""

from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon


def create_tray_icon(app):
    """Show an app-owned indicator, including while its windows are hidden."""
    icon_path = Path(__file__).parent / "assets" / "tray-icon.svg"
    tray = QSystemTrayIcon(QIcon(str(icon_path)), app)
    tray.setToolTip("Shortcut Cheatsheet")
    app.aboutToQuit.connect(tray.hide)
    tray.show()
    return tray
