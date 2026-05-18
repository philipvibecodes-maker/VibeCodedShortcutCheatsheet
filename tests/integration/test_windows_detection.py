"""Integration tests hitting real Win32 window-management APIs.

Skipped on non-Windows. Must run inside the Windows VM.
"""

import sys
import subprocess
import time

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "win32", reason="Windows only"),
]


def test_platform_supported_on_windows():
    from src.platform.windows.window_detection import is_platform_supported
    ok, _ = is_platform_supported()
    assert ok is True


def test_detect_notepad_foreground():
    """Launch Notepad and verify the detection backend reports it."""
    from src.platform.windows.window_detection import get_focused_app_name

    proc = subprocess.Popen(["notepad.exe"])
    try:
        # Give Notepad a moment to actually become foreground
        for _ in range(20):
            time.sleep(0.25)
            name = get_focused_app_name()
            if name and "notepad" in name.lower():
                return
        pytest.fail(f"Notepad did not become foreground; last seen: {name!r}")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
