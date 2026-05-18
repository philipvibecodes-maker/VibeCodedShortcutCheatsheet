"""Integration tests hitting the real GNOME Shell window-calls DBus API.

Skipped on non-Linux. Requires the window-calls extension to be active.
"""

import sys

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only"),
]


def test_platform_supported_on_this_system():
    from src.platform.linux_gnome.gnome_window_detection import is_platform_supported
    ok, message = is_platform_supported()
    if not ok:
        pytest.skip(f"window-calls extension not available: {message}")
    assert ok is True


def test_get_open_windows_returns_list():
    from src.platform.linux_gnome.gnome_window_detection import (
        is_platform_supported,
        get_open_windows,
    )
    ok, _ = is_platform_supported()
    if not ok:
        pytest.skip("window-calls extension not available")
    windows = get_open_windows()
    assert isinstance(windows, list)
    if windows:
        assert "wm_class" in windows[0]


def test_get_work_area_returns_sensible_dims():
    from src.platform.linux_gnome.window_movement import get_work_area
    work = get_work_area()
    if work is None:
        pytest.skip("xprop / _NET_WORKAREA not available (Wayland-only?)")
    assert work["width"] > 0
    assert work["height"] > 0
