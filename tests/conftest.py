"""Shared pytest fixtures."""

import sys
from pathlib import Path

# Make `src` imports work from anywhere in the suite
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import pytest


@pytest.fixture
def sample_windows():
    """A minimal list of fake windows in the shape the backends return."""
    return [
        {"wm_class": "brave-browser", "focus": False, "id": 1},
        {"wm_class": "dev.zed.Zed", "focus": True, "id": 2},
        {"wm_class": "gnome-terminal-server", "focus": False, "id": 3},
    ]


@pytest.fixture
def mock_platform(monkeypatch, sample_windows):
    """Monkeypatch the platform dispatch layer so tests never touch the real OS."""
    from src import platform as platform_module

    monkeypatch.setattr(platform_module, "get_open_windows", lambda: list(sample_windows))
    monkeypatch.setattr(
        platform_module, "get_open_app_names",
        lambda: [w["wm_class"] for w in sample_windows],
    )
    monkeypatch.setattr(
        platform_module, "get_focused_window",
        lambda: next((w for w in sample_windows if w.get("focus")), None),
    )
    monkeypatch.setattr(
        platform_module, "get_focused_app_name",
        lambda: next((w["wm_class"] for w in sample_windows if w.get("focus")), None),
    )
    monkeypatch.setattr(platform_module, "is_platform_supported", lambda: (True, ""))
    return platform_module
