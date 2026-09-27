"""Regression tests for cheatsheet launch/second-instance behavior.

Window detection and positioning are mocked and Qt runs offscreen, so no
real windows are opened or focused.

These tests reproduce a reported bug:
  1. Launching the app while the focused app has no shortcuts does nothing,
     instead of opening the "add shortcuts" settings window.
  2. Launching a second time opens the "add shortcuts" settings window even
     when the focused app already has recorded shortcuts — it should reopen
     the cheatsheet instead.
"""

import json

import pytest

import src.cheatsheet.cheatsheet_window as cw_module
from src import data_storage
from src.cheatsheet.cheatsheet_window import CheatsheetWindow

APP_WITH_SHORTCUTS = "brave-browser"
APP_WITHOUT_SHORTCUTS = "ghost-app"


def _write_app(tmp_path, app_name, shortcuts):
    (tmp_path / f"{app_name}.json").write_text(json.dumps({
        "app_name": app_name,
        "display_name": app_name,
        "shortcuts": shortcuts,
    }))


@pytest.fixture
def focused_window():
    """Mutable stand-in for the OS-reported focused window.

    Tests change ``wm_class`` to simulate focus moving between apps.
    """
    return {"wm_class": APP_WITHOUT_SHORTCUTS, "title": "Ghost Window", "focus": True, "id": 1}


@pytest.fixture
def mock_env(tmp_path, monkeypatch, focused_window):
    """Redirect shortcut storage to tmp_path and mock window detection."""
    monkeypatch.setattr(data_storage, "get_data_dir", lambda: tmp_path)
    _write_app(tmp_path, APP_WITH_SHORTCUTS, [{"keys": "Ctrl+T", "description": "New tab"}])
    _write_app(tmp_path, "default", [{"keys": "Super", "description": "Overview"}])

    monkeypatch.setattr(cw_module, "get_focused_window", lambda: focused_window)
    monkeypatch.setattr(cw_module, "get_corner_position", lambda *args: (0, 0))
    return tmp_path


@pytest.fixture
def cheatsheet(qtbot, mock_env):
    """A shown CheatsheetWindow with its poll timer stopped (tests drive
    ``_on_poll`` manually). Scheduled zero-timers are flushed so the
    started-hidden path settles before the test body runs."""
    window = CheatsheetWindow()
    qtbot.addWidget(window)
    window._poll_timer.stop()
    window.show()
    qtbot.wait(50)
    return window


def _settings_visible(window):
    return window._settings_window is not None and window._settings_window.isVisible()


# --- Behavior that already works (controls) ---


def test_first_launch_with_shortcuts_shows_cheatsheet(qtbot, mock_env, focused_window):
    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    window = CheatsheetWindow()
    qtbot.addWidget(window)
    window._poll_timer.stop()
    window.show()
    qtbot.wait(50)
    assert window.isVisible()
    assert not _settings_visible(window)


def test_poll_hides_when_focused_app_has_no_shortcuts(cheatsheet, focused_window):
    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    cheatsheet._on_poll()
    assert cheatsheet.isVisible()

    focused_window["wm_class"] = APP_WITHOUT_SHORTCUTS
    cheatsheet._on_poll()
    assert not cheatsheet.isVisible()


def test_poll_reopens_when_focused_app_has_shortcuts(cheatsheet, focused_window):
    assert not cheatsheet.isVisible()  # started hidden on ghost-app
    # Dismiss the add-shortcuts window that first launch opened
    cheatsheet._settings_window.close()

    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    cheatsheet._on_poll()
    assert cheatsheet.isVisible()
    assert not _settings_visible(cheatsheet)


def test_second_launch_without_shortcuts_opens_add_shortcuts(cheatsheet):
    """Second launch while hidden correctly opens settings for the unknown app."""
    cheatsheet.handle_second_instance(APP_WITHOUT_SHORTCUTS)
    assert _settings_visible(cheatsheet)
    assert cheatsheet._settings_window.app_combo.currentData() == APP_WITHOUT_SHORTCUTS


# --- Bug reproductions ---


def test_first_launch_without_shortcuts_opens_add_shortcuts(qtbot, mock_env):
    """BUG: launching while the focused app has no shortcuts should open the
    "add shortcuts" window. Currently nothing appears — the window hides."""
    window = CheatsheetWindow()
    qtbot.addWidget(window)
    window._poll_timer.stop()
    window.show()
    qtbot.wait(50)

    assert not window.isVisible()
    assert _settings_visible(window), (
        "first launch with an unprofiled app should open the add-shortcuts window"
    )
    assert window._settings_window.app_combo.currentData() == APP_WITHOUT_SHORTCUTS


def test_second_launch_with_shortcuts_reopens_cheatsheet(cheatsheet):
    """BUG: a second launch while the focused app has recorded shortcuts should
    reopen the cheatsheet. Currently the add-shortcuts window opens instead."""
    assert not cheatsheet.isVisible()  # hidden after first launch on ghost-app
    # Dismiss the add-shortcuts window that first launch opened
    cheatsheet._settings_window.close()

    cheatsheet.handle_second_instance(APP_WITH_SHORTCUTS)

    assert cheatsheet.isVisible(), "cheatsheet should reopen for a profiled app"
    assert not _settings_visible(cheatsheet), (
        "add-shortcuts window must not open for an app that already has shortcuts"
    )
