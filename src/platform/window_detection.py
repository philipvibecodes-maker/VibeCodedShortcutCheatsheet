import json
import subprocess


def is_window_calls_available():
    """Check whether the window-calls Gnome extension is installed and enabled."""
    result = subprocess.run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Shell",
            "--object-path", "/org/gnome/Shell/Extensions/Windows",
            "--method", "org.gnome.Shell.Extensions.Windows.List",
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_open_windows():
    """Return a list of window dicts from the window-calls DBus extension."""
    result = subprocess.run(
        [
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Shell",
            "--object-path", "/org/gnome/Shell/Extensions/Windows",
            "--method", "org.gnome.Shell.Extensions.Windows.List",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gdbus call failed: {result.stderr.strip()}")
    # gdbus wraps the return in ('...',) — extract the JSON string
    raw = result.stdout.strip()
    json_str = raw[2:-3]
    return json.loads(json_str)


def get_open_app_names():
    """Return a list of application names (wm_class) for all open windows."""
    windows = get_open_windows()
    return [w["wm_class"] for w in windows]


def get_focused_window():
    """Return the window dict for the currently focused window, or None if no window has focus."""
    windows = get_open_windows()
    for window in windows:
        if window.get("focus"):
            return window
    return None


def get_focused_app_name():
    """Return the application name (wm_class) of the currently focused window, or None if no window has focus."""
    focused = get_focused_window()
    if focused:
        return focused.get("wm_class")
    return None
