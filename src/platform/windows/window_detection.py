"""Windows window-detection backend via the Win32 API (ctypes, no extra deps).

`wm_class` is the owning process's executable name ("notepad.exe",
"Code.exe", ...) — the closest Windows analogue of X11's WM_CLASS and the
name to use for data/<app>.json files. For UWP apps, whose top-level
window is hosted by ApplicationFrameHost.exe, the hosted app's process
name is resolved instead.
"""

import ctypes
from ctypes import wintypes
from pathlib import Path

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    _dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
except OSError:
    _dwmapi = None

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_GW_OWNER = 4
_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_APPWINDOW = 0x00040000
_DWMWA_CLOAKED = 14

# Top-level shell/special windows that EnumWindows reports but that aren't
# applications the user can switch to.
_SHELL_CLASSES = {
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "Windows.UI.Core.CoreWindow",
    "WindowsDashboard",
    "XamlExplorerHostIslandWindow",
}

_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
_user32.EnumChildWindows.argtypes = [wintypes.HWND, _WNDENUMPROC, wintypes.LPARAM]
_user32.EnumChildWindows.restype = wintypes.BOOL
_user32.GetForegroundWindow.argtypes = []
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowVisible.restype = wintypes.BOOL
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, wintypes.LPDWORD]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetWindow.restype = wintypes.HWND
_user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype = ctypes.c_long

_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, wintypes.LPDWORD,
]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

if _dwmapi is not None:
    _dwmapi.DwmGetWindowAttribute.argtypes = [
        wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
    ]
    _dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long  # HRESULT


def is_platform_supported():
    """Return (ok, message). No external dependencies needed on Windows."""
    return (True, "")


def _window_text(hwnd):
    length = _user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    if _user32.GetClassNameW(hwnd, buf, len(buf)) == 0:
        return ""
    return buf.value


def _window_pid(hwnd):
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _process_image_name(pid):
    """Return the executable file name for a pid, or None if it can't be queried."""
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return Path(buf.value).name
        return None
    finally:
        _kernel32.CloseHandle(handle)


def _hosted_app_name(hwnd):
    """Resolve the real process name inside an ApplicationFrameHost UWP window."""
    core_windows = []

    @_WNDENUMPROC
    def on_child(child_hwnd, _lparam):
        if _class_name(child_hwnd) == "Windows.UI.Core.CoreWindow":
            core_windows.append(child_hwnd)
            return False
        return True

    _user32.EnumChildWindows(hwnd, on_child, 0)
    if not core_windows:
        return None
    return _process_image_name(_window_pid(core_windows[0]))


def _window_process_name(hwnd):
    name = _process_image_name(_window_pid(hwnd))
    if name == "ApplicationFrameHost.exe":
        name = _hosted_app_name(hwnd) or name
    return name


def _is_cloaked(hwnd):
    """DWM-cloaked windows (UWP background apps, hidden shell windows)."""
    if _dwmapi is None:
        return False
    cloaked = wintypes.DWORD(0)
    hr = _dwmapi.DwmGetWindowAttribute(
        hwnd, _DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
    )
    return hr == 0 and cloaked.value != 0


def _is_app_window(hwnd):
    """Match the windows a user sees in the taskbar / Alt-Tab list."""
    if not _user32.IsWindowVisible(hwnd):
        return False
    if _class_name(hwnd) in _SHELL_CLASSES:
        return False
    if _is_cloaked(hwnd):
        return False
    exstyle = _user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
    if exstyle & _WS_EX_TOOLWINDOW and not exstyle & _WS_EX_APPWINDOW:
        return False
    if _user32.GetWindow(hwnd, _GW_OWNER):
        return False
    return True


def _window_dict(hwnd, foreground_hwnd):
    return {
        "id": int(hwnd),
        "title": _window_text(hwnd),
        "wm_class": _window_process_name(hwnd),
        "focus": hwnd == foreground_hwnd,
    }


def get_open_windows():
    """Return a list of window dicts for visible application windows."""
    hwnds = []

    @_WNDENUMPROC
    def on_window(hwnd, _lparam):
        if _is_app_window(hwnd):
            hwnds.append(hwnd)
        return True

    _user32.EnumWindows(on_window, 0)
    foreground = _user32.GetForegroundWindow()
    return [_window_dict(hwnd, foreground) for hwnd in hwnds]


def get_open_app_names():
    """Return the executable name of every open application window."""
    return [w["wm_class"] for w in get_open_windows() if w.get("wm_class")]


def get_focused_window():
    """Return the window dict for the foreground window, or None.

    Shell windows (taskbar, desktop, Start menu) are treated as "no app
    focused" so clicking them doesn't resolve to their explorer.exe owner.
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    if _class_name(hwnd) in _SHELL_CLASSES:
        return None
    return _window_dict(hwnd, hwnd)


def get_focused_app_name():
    """Return the executable name of the foreground window, or None."""
    focused = get_focused_window()
    if focused:
        return focused.get("wm_class")
    return None
