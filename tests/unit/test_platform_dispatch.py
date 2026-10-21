"""Verify the dispatch layer exposes the expected public API and routes by OS."""

import sys

from src import platform as platform_module


PUBLIC_API = [
    "is_platform_supported",
    "get_open_windows",
    "get_open_app_names",
    "get_focused_window",
    "get_focused_app_name",
    "get_work_area",
    "get_corner_position",
]


def test_public_api_surface_exists():
    for name in PUBLIC_API:
        assert hasattr(platform_module, name), f"platform dispatch missing: {name}"


def test_public_api_members_are_callable():
    for name in PUBLIC_API:
        assert callable(getattr(platform_module, name))


def test_dispatch_matches_current_os():
    if sys.platform.startswith("linux"):
        import os
        if os.environ.get("XDG_SESSION_TYPE") == "x11":
            from src.platform.linux_gnome import x11_window_detection
            assert platform_module.get_focused_window is x11_window_detection.get_focused_window
        else:
            from src.platform.linux_gnome import gnome_window_detection
            assert platform_module.get_focused_window is gnome_window_detection.get_focused_window
    elif sys.platform == "win32":
        from src.platform.windows import window_detection as win_detection
        assert platform_module.get_focused_window is win_detection.get_focused_window
