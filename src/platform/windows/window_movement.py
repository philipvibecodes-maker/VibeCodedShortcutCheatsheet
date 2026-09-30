"""Windows window-movement backend.

Qt is natively supported on Windows, so positioning is pure PyQt6:
`QScreen.availableGeometry()` is the taskbar-aware work area in the same
logical-pixel coordinate space that `QWidget.move()` expects — no Win32
code is needed.
"""

from PyQt6.QtGui import QGuiApplication


def get_work_area():
    """Return {x, y, width, height} of the primary screen's usable area
    (screen minus taskbar and other reserved edges), or None."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    g = screen.availableGeometry()
    return {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}


def get_corner_position(window, corner_v, corner_h):
    """Return (x, y) to position a QWidget in the given corner of the work
    area of the screen it is on, or None if no screen is available."""
    screen = window.screen() or QGuiApplication.primaryScreen()
    if screen is None:
        return None
    area = screen.availableGeometry()

    frame = window.frameGeometry()
    win_width = frame.width()
    win_height = frame.height()

    if corner_h == "left":
        x = area.x()
    else:
        x = area.x() + area.width() - win_width

    if corner_v == "top":
        y = area.y()
    else:
        y = area.y() + area.height() - win_height

    return (x, y)
