"""Registers a GNOME custom keybinding (Ctrl+Shift+\\) that toggles the notes window.

GNOME custom keybindings run a shell command, so the binding launches
`main.py --toggle-notes`, which forwards a toggle message to the running
instance over the QLocalSocket.
"""

import ast
import subprocess
import sys
from pathlib import Path

_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
_LIST_KEY = "custom-keybindings"
_PATH_PREFIX = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
_BINDING = "<Primary><Shift>backslash"
_NAME = "Shortcut Cheatsheet: toggle notes"


def toggle_command() -> str:
    """The shell command the keybinding runs."""
    main_py = Path(__file__).resolve().parents[3] / "main.py"
    return f"{sys.executable} {main_py} --toggle-notes"


def _gsettings(*args: str) -> str:
    return subprocess.run(
        ["gsettings", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _parse_path_list(raw: str) -> list:
    """Parse the GVariant string list gsettings returns (e.g. "['/a/', '/b/']" or "@as []")."""
    if raw.startswith("@"):
        return []
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    return list(value) if isinstance(value, (list, tuple)) else []


def _custom_paths() -> list:
    return _parse_path_list(_gsettings("get", _SCHEMA, _LIST_KEY))


def _write_path_list(paths: list) -> None:
    rendered = "[" + ", ".join(f"'{p}'" for p in paths) + "]"
    _gsettings("set", _SCHEMA, _LIST_KEY, rendered)


def _free_path(existing: list) -> str:
    i = 0
    while f"{_PATH_PREFIX}custom{i}/" in existing:
        i += 1
    return f"{_PATH_PREFIX}custom{i}/"


def register_notes_hotkey() -> None:
    """Idempotently register the Ctrl+Shift+\\ global keybinding."""
    command = toggle_command()
    paths = _custom_paths()
    for path in paths:
        existing = _gsettings("get", f"{_SCHEMA}.custom-keybinding:{path}", "command")
        if existing.strip("'") == command:
            return  # already registered
    path = _free_path(paths)
    schema = f"{_SCHEMA}.custom-keybinding:{path}"
    _gsettings("set", schema, "name", _NAME)
    _gsettings("set", schema, "command", command)
    _gsettings("set", schema, "binding", _BINDING)
    _write_path_list(paths + [path])
