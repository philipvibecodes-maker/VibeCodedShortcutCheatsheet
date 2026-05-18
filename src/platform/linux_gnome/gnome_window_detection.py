import json
import subprocess


_MISSING_EXTENSION_MESSAGE = (
    'The "window-calls" Gnome extension is required but not found.\n\n'
    'Install it from:\n'
    'https://extensions.gnome.org/extension/4724/window-calls/'
)


def is_platform_supported():
    """Return (ok, message). Checks the window-calls Gnome extension is available."""
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
    if result.returncode == 0:
        return (True, "")
    return (False, _MISSING_EXTENSION_MESSAGE)


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
