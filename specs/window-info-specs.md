## Specifications for module to retrieve information about open window

### Linux
The application assumes that the user has installed the "window calls" gnome extension,
which enables detecting the currently focused window on Wayland through DBUS.
Note: window-calls is used for window *detection* only, not for window movement.

Relevant documentation:
https://github.com/ickyicky/window-calls
https://extensions.gnome.org/extension/4724/window-calls

### Windows
Detection uses the Win32 API directly via ctypes (no extra dependencies):
`EnumWindows` + `IsWindowVisible`/`GetWindowText`/`GetClassName` for the
window list, `GetForegroundWindow` for focus, and
`GetWindowThreadProcessId` + `QueryFullProcessImageName` to resolve the
owning executable name, which is used as `wm_class`. Windows hosted by
`ApplicationFrameHost.exe` (UWP apps) are resolved to the hosted app's
process. DWM-cloaked windows, tool windows, owned popups, and shell
windows (taskbar, desktop, Start menu) are filtered out of the window
list. `get_focused_window` reports whatever window is foreground,
filtered or not.
