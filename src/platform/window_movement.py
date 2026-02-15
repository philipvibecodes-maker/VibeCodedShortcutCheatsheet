import subprocess

from src.platform.window_detection import get_open_windows


def get_window_id_by_app_name(app_name):
    """Return the window-calls ID for the first window matching app_name (wm_class)."""
    windows = get_open_windows()
    for window in windows:
        if window.get("wm_class") == app_name:
            return window.get("id")
    return None


def get_work_area():
    """Return the work area (x, y, width, height) in physical pixels.

    Uses _NET_WORKAREA from XWayland, which accounts for GNOME panels/bars.
    """
    result = subprocess.run(
        ["xprop", "-root", "_NET_WORKAREA"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    # Format: _NET_WORKAREA(CARDINAL) = x, y, w, h, x, y, w, h, ...
    parts = result.stdout.strip().split("=", 1)
    if len(parts) != 2:
        return None
    values = [int(v.strip()) for v in parts[1].split(",")[:4]]
    return {"x": values[0], "y": values[1], "width": values[2], "height": values[3]}


def get_corner_position(window, corner_v, corner_h):
    """Return (x, y) to position a QWidget in the given screen corner.

    Uses frameGeometry() to account for window decorations (titlebar, borders).
    Returns None if the work area cannot be determined.
    """
    work_area = get_work_area()
    if not work_area:
        return None

    frame = window.frameGeometry()
    win_width = frame.width()
    win_height = frame.height()

    if corner_h == "left":
        x = work_area["x"]
    else:
        x = work_area["x"] + work_area["width"] - win_width

    if corner_v == "top":
        y = 0
    else:
        y = work_area["y"] + work_area["height"] - win_height

    return (x, y)
