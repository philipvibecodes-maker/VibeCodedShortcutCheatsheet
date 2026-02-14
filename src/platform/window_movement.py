import json
import subprocess

from src.platform.window_detection import get_open_windows


def get_window_id_by_app_name(app_name):
    """Return the window-calls ID for the first window matching app_name (wm_class)."""
    windows = get_open_windows()
    for window in windows:
        if window.get("wm_class") == app_name:
            return window.get("id")
    return None


def get_window_id_by_title(title):
    """Return the window-calls ID for the first window matching the given title."""
    windows = get_open_windows()
    for window in windows:
        if window.get("title") == title:
            return window.get("id")
    return None


def get_window_details(window_id):
    """Return the window details dict from the window-calls DBus extension.

    Includes WM-reported position (x, y) and size (width, height) in physical pixels,
    which accounts for server-side decorations (titlebar, borders).
    """
    result = subprocess.run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Shell",
            "--object-path", "/org/gnome/Shell/Extensions/Windows",
            "--method", "org.gnome.Shell.Extensions.Windows.Details",
            str(window_id),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gdbus Details failed: {result.stderr.strip()}")
    raw = result.stdout.strip()
    json_str = raw[2:-3]
    return json.loads(json_str)


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


def move_window(window_id, x, y):
    """Move a window to (x, y) using the window-calls DBus extension."""
    result = subprocess.run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Shell",
            "--object-path", "/org/gnome/Shell/Extensions/Windows",
            "--method", "org.gnome.Shell.Extensions.Windows.Move",
            str(window_id), str(x), str(y),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gdbus Move failed: {result.stderr.strip()}")
