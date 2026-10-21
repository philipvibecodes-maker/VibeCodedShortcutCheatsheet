"""X11 window detection via libX11/EWMH properties (ctypes, no subprocess).

Used on X11 sessions (XDG_SESSION_TYPE=x11) instead of the window-calls GNOME
extension. Reads _NET_ACTIVE_WINDOW/_NET_CLIENT_LIST/WM_CLASS/_NET_WM_NAME
directly, which benchmarked ~50x faster than the gdbus subprocess path
(see docs/x11-window-detection-benchmark.md). Wayland keeps window-calls.
"""

import ctypes
from ctypes.util import find_library
from typing import Optional

_MISSING_DISPLAY_MESSAGE = (
    "An X11 display is required but could not be opened.\n\n"
    "Ensure DISPLAY is set and the X server is reachable."
)

_lib = ctypes.CDLL(find_library("X11") or "libX11.so.6")

_lib.XOpenDisplay.restype = ctypes.c_void_p
_lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
_lib.XDefaultScreenOfDisplay.restype = ctypes.c_void_p
_lib.XDefaultScreenOfDisplay.argtypes = [ctypes.c_void_p]
_lib.XRootWindowOfScreen.restype = ctypes.c_ulong
_lib.XRootWindowOfScreen.argtypes = [ctypes.c_void_p]
_lib.XInternAtom.restype = ctypes.c_ulong
_lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
_lib.XGetWindowProperty.restype = ctypes.c_int
_lib.XGetWindowProperty.argtypes = [
    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
    ctypes.c_long, ctypes.c_long, ctypes.c_int, ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
]
_lib.XFree.argtypes = [ctypes.c_void_p]

_display = None
_atom_cache = {}


def _xdisplay():
    """Return the shared X display handle, opening it on first use."""
    global _display
    if _display is None:
        _display = _lib.XOpenDisplay(None)
        if not _display:
            raise RuntimeError(_MISSING_DISPLAY_MESSAGE)
    return _display


def _atom(name):
    atom = _atom_cache.get(name)
    if atom is None:
        atom = _lib.XInternAtom(_xdisplay(), name.encode(), 0)
        _atom_cache[name] = atom
    return atom


def _root_window():
    d = _xdisplay()
    return _lib.XRootWindowOfScreen(_lib.XDefaultScreenOfDisplay(d))


def _read_property(window, atom, max_items=1024):
    """Return the property as a list of ints (format 16/32) or bytes (format 8).

    Returns None when the property is absent or the read fails.
    """
    actual_type = ctypes.c_ulong()
    actual_format = ctypes.c_int()
    nitems = ctypes.c_ulong()
    bytes_after = ctypes.c_ulong()
    prop = ctypes.POINTER(ctypes.c_ubyte)()
    status = _lib.XGetWindowProperty(
        _xdisplay(), window, atom, 0, max_items, 0, 0,
        ctypes.byref(actual_type), ctypes.byref(actual_format),
        ctypes.byref(nitems), ctypes.byref(bytes_after), ctypes.byref(prop),
    )
    if status != 0 or not prop:
        return None
    try:
        if actual_format.value == 32:
            # 32-bit items are stored in machine 'long' slots
            arr = ctypes.cast(prop, ctypes.POINTER(ctypes.c_long))
            return [arr[i] for i in range(nitems.value)]
        if actual_format.value == 16:
            arr = ctypes.cast(prop, ctypes.POINTER(ctypes.c_ushort))
            return [arr[i] for i in range(nitems.value)]
        if actual_format.value == 8:
            return ctypes.string_at(prop, nitems.value)
        return None
    finally:
        _lib.XFree(prop)


def _text_property(window, atom_name):
    """Read a text property, decoding as UTF-8 with latin-1 fallback."""
    raw = _read_property(window, _atom(atom_name))
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _window_title(window):
    return _text_property(window, "_NET_WM_NAME") or _text_property(window, "WM_NAME")


def _window_class(window):
    """WM_CLASS is two NUL-separated strings: 'instance\\0class\\0'. Prefer class."""
    raw = _read_property(window, _atom("WM_CLASS"))
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    parts = [p for p in raw.split(b"\x00") if p]
    if not parts:
        return ""
    chosen = parts[-1] if len(parts) > 1 else parts[0]
    return chosen.decode("utf-8", errors="replace")


def _window_pid(window):
    values = _read_property(window, _atom("_NET_WM_PID"))
    return values[0] if isinstance(values, list) and values else 0


def _active_window_id():
    values = _read_property(_root_window(), _atom("_NET_ACTIVE_WINDOW"))
    return values[0] if isinstance(values, list) and values else 0


def _describe_window(window, active_id):
    return {
        "id": window,
        "wm_class": _window_class(window),
        "title": _window_title(window),
        "pid": _window_pid(window),
        "focus": window == active_id,
    }


def is_platform_supported():
    """Return (ok, message). An openable X display is all that's required."""
    try:
        _xdisplay()
    except RuntimeError:
        return (False, _MISSING_DISPLAY_MESSAGE)
    return (True, "")


def get_open_windows():
    """Return all client windows from _NET_CLIENT_LIST as window dicts."""
    ids = _read_property(_root_window(), _atom("_NET_CLIENT_LIST")) or []
    active = _active_window_id()
    return [_describe_window(w, active) for w in ids]


def get_open_app_names():
    """Return the application name (wm_class) of every open window."""
    return [w["wm_class"] for w in get_open_windows()]


def get_focused_window() -> Optional[dict]:
    """Return the focused window's dict, or None if no client window has focus."""
    active = _active_window_id()
    if not active:
        return None
    return _describe_window(active, active)


def get_focused_app_name() -> Optional[str]:
    """Return the focused window's wm_class, or None."""
    focused = get_focused_window()
    return focused["wm_class"] if focused else None
