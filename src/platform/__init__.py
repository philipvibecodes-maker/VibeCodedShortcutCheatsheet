"""Platform dispatch layer.

Selects and re-exports the appropriate backend for the current OS. Callers
should always import from `src.platform` — never from a concrete backend —
so platform routing stays in one place.
"""

import sys

if sys.platform.startswith("linux"):
    from src.platform.linux_gnome.gnome_window_detection import (
        is_platform_supported,
        get_open_windows,
        get_open_app_names,
        get_focused_window,
        get_focused_app_name,
    )
    from src.platform.linux_gnome.window_movement import (
        get_work_area,
        get_corner_position,
    )
elif sys.platform == "win32":
    from src.platform.windows.window_detection import (
        is_platform_supported,
        get_open_windows,
        get_open_app_names,
        get_focused_window,
        get_focused_app_name,
    )
    from src.platform.windows.window_movement import (
        get_work_area,
        get_corner_position,
    )
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")

__all__ = [
    "is_platform_supported",
    "get_open_windows",
    "get_open_app_names",
    "get_focused_window",
    "get_focused_app_name",
    "get_work_area",
    "get_corner_position",
]
