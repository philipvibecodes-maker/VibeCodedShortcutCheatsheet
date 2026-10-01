"""Windows window-pinning backend.

Intentionally empty: pinning is handled by Qt itself — the cheatsheet
window sets Qt.WindowType.WindowStaysOnTopHint, which Win32 honors. See
the matching no-op module in linux_gnome.
"""
