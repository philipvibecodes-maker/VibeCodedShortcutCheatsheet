"""A passive system tray indicator for the running application."""

from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QSystemTrayIcon

from src.version import APP_REVISION


def revision_icon():
    """Render a numbered badge into the icon (also visible without tooltips)."""
    icon_path = Path(__file__).parent / "assets" / "tray-icon.svg"
    icon = QIcon()
    for size in (22, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        QIcon(str(icon_path)).paint(painter, QRect(0, 0, size, size))
        badge = QRect(size // 3, size // 3, size - size // 3, size - size // 3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2563eb"))
        painter.drawRoundedRect(badge, size / 8, size / 8)
        font = QFont("Sans Serif")
        font.setBold(True)
        font.setPixelSize(round(size * (0.48 if APP_REVISION < 100 else 0.32)))
        painter.setFont(font)
        painter.setPen(QColor("white"))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(APP_REVISION))
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def create_tray_icon(app):
    """Show an app-owned indicator, including while its windows are hidden."""
    tray = QSystemTrayIcon(revision_icon(), app)
    tray.setToolTip(f"Shortcut Cheatsheet — revision {APP_REVISION}")
    app.aboutToQuit.connect(tray.hide)
    tray.show()
    return tray
