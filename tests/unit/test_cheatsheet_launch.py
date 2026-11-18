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


def test_terminal_title_updates_preserve_shortcut_widgets(cheatsheet, focused_window):
    """Changing command/title text must not tear down unchanged shortcuts."""
    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    cheatsheet._on_poll()
    grid = cheatsheet.grid_widget
    geometry = cheatsheet.close_button.geometry()
    window_size = cheatsheet.size()

    for title in ("terminal: running command", "terminal: output", "terminal: prompt"):
        focused_window["title"] = title
        cheatsheet._on_poll()
        assert cheatsheet.grid_widget is grid
        assert cheatsheet.close_button.geometry() == geometry
        assert cheatsheet.size() == window_size
        assert cheatsheet._current_title == title


def test_title_profile_change_replaces_grid_without_detaching(cheatsheet, focused_window):
    """Title-dependent profiles still refresh, without creating top-level grids."""
    data_storage.save_tab_shortcuts(APP_WITH_SHORTCUTS, "editor", [
        {"keys": "Ctrl+S", "description": "Save document"},
    ])
    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    cheatsheet._on_poll()
    old_grid = cheatsheet.grid_widget
    focused_window["title"] = "terminal: editor"
    cheatsheet._on_poll()

    assert cheatsheet.grid_widget is not old_grid
    assert old_grid.parent() is cheatsheet.central
    assert old_grid.isHidden()
    assert cheatsheet.grid_layout.itemAtPosition(0, 0).widget().text() == "Save document"


def test_editing_displayed_shortcuts_refreshes_grid(cheatsheet, focused_window):
    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    cheatsheet._on_poll()
    old_grid = cheatsheet.grid_widget
    data_storage.save_app_shortcuts(APP_WITH_SHORTCUTS, [
        {"keys": "Ctrl+W", "description": "Close tab"},
    ])
    cheatsheet._on_shortcuts_saved(APP_WITH_SHORTCUTS)

    assert cheatsheet.grid_widget is not old_grid
    assert cheatsheet.grid_layout.itemAtPosition(0, 0).widget().text() == "Close tab"


def test_second_launch_without_shortcuts_opens_add_shortcuts(cheatsheet):
    """Second launch while hidden correctly opens settings for the unknown app."""
    cheatsheet.handle_second_instance(APP_WITHOUT_SHORTCUTS)
    assert _settings_visible(cheatsheet)
    assert cheatsheet._settings_window.app_combo.currentData() == APP_WITHOUT_SHORTCUTS


def test_toggle_notes_launch_keeps_windows_hidden(qtbot, mock_env):
    """A --toggle-notes launch (open_settings_for_new_app=False) must not
    surface the cheatsheet or the add-shortcuts settings window."""
    window = CheatsheetWindow(open_settings_for_new_app=False)
    qtbot.addWidget(window)
    window._poll_timer.stop()
    qtbot.wait(50)

    assert not window.isVisible()
    assert not _settings_visible(window)


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


def test_toggle_after_app_delete_does_not_reopen_settings(cheatsheet, focused_window):
    """Deleting the focused app's profile, then toggling, must not re-point the
    (still open) settings window at the deleted app — the deletion was
    deliberate, not a request to re-add it."""
    data_storage.save_skip_delete_confirmation(True)

    # Dismiss the add-shortcuts window that first launch opened for ghost-app
    cheatsheet._settings_window.close()

    focused_window["wm_class"] = APP_WITH_SHORTCUTS
    cheatsheet._on_poll()
    assert cheatsheet.isVisible()

    cheatsheet._open_settings()
    cheatsheet._settings_window._delete_app()
    assert _settings_visible(cheatsheet)  # settings stays open after delete
    assert cheatsheet._settings_window.app_combo.currentData() != APP_WITH_SHORTCUTS

    cheatsheet.handle_second_instance(APP_WITH_SHORTCUTS, "Brave Window")

    assert not cheatsheet.isVisible()
    assert cheatsheet._settings_window.app_combo.currentData() != APP_WITH_SHORTCUTS, (
        "toggle must not reopen add-shortcuts for the app that was just deleted"
    )
