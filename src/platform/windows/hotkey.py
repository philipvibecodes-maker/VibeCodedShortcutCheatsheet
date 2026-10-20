"""Registers a global Ctrl+Shift+\\ hotkey on Windows via RegisterHotKey.

The hotkey posts WM_HOTKEY to the app's thread message queue; a
QAbstractNativeEventFilter turns it into a callback that toggles the
notes window.
"""

import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter

_user32 = ctypes.WinDLL("user32", use_last_error=True)

MOD_NOREPEAT = 0x4000
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_OEM_5 = 0xDC  # the '\' key
WM_HOTKEY = 0x0312
HOTKEY_ID = 1


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
    ]


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):
        msg = _MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            self._callback()
            return True, 0
        return False, 0


def install_notes_hotkey(callback):
    """Register Ctrl+Shift+\\ globally; `callback` runs on each press.

    Returns the event filter (keep a reference or it gets garbage-collected).
    hwnd=None makes the hotkey thread-scoped so it fires even when our
    window isn't focused.
    """
    if not _user32.RegisterHotKey(
        None, HOTKEY_ID, MOD_NOREPEAT | MOD_CONTROL | MOD_SHIFT, VK_OEM_5
    ):
        raise OSError("RegisterHotKey failed")
    event_filter = _HotkeyFilter(callback)
    from PyQt6.QtWidgets import QApplication

    QApplication.instance().installNativeEventFilter(event_filter)
    return event_filter


def uninstall_notes_hotkey():
    _user32.UnregisterHotKey(None, HOTKEY_ID)
