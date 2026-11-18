"""Unit tests for NotesWindow topic selection persistence.

Runs offscreen with data storage redirected to a tmp dir.
"""

import json

import pytest
from PyQt6.QtCore import QAbstractAnimation, Qt

from src import data_storage
from src.notes.notes_window import NotesWindow


@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(data_storage, "get_data_dir", lambda: tmp_path)
    return tmp_path


def _make_window(qtbot):
    window = NotesWindow()
    qtbot.addWidget(window)
    return window


def test_defaults_to_first_topic(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.add_topic("beta")
    window = _make_window(qtbot)
    assert window._current_topic() == "alpha"


def test_restores_last_shown_topic(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.add_topic("beta")
    data_storage.save_notes_last_topic("beta")
    window = _make_window(qtbot)
    assert window._current_topic() == "beta"


def test_missing_last_topic_falls_back_to_first(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.save_notes_last_topic("deleted-topic")
    window = _make_window(qtbot)
    assert window._current_topic() == "alpha"


def test_selecting_topic_persists(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.add_topic("beta")
    window = _make_window(qtbot)
    window.topic_list.setCurrentRow(1)
    assert data_storage.get_notes_last_topic() == "beta"


def test_restores_last_search_selected(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.save_notes_last_search("hello")
    window = _make_window(qtbot)
    assert window.search_edit.text() == "hello"
    assert window.search_edit.selectedText() == "hello"


def test_typing_search_persists(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    window = _make_window(qtbot)
    window.search_edit.setText("abc")
    assert data_storage.get_notes_last_search() == "abc"


@pytest.mark.parametrize("topic_row", [0, 1])
def test_clicking_topic_exits_search(qtbot, temp_data_dir, topic_row):
    for topic in ("alpha", "beta"):
        data_storage.add_topic(topic)
        data_storage.add_topic_entry(topic, topic + " key", "value")
    window = _make_window(qtbot)
    window.show()
    window.search_edit.setText("no matches")
    assert window.table.rowCount() == 0
    item = window.topic_list.item(topic_row)
    qtbot.mouseClick(window.topic_list.viewport(), Qt.MouseButton.LeftButton,
                     pos=window.topic_list.visualItemRect(item).center())
    assert window.search_edit.text() == ""
    assert data_storage.get_notes_last_search() == ""
    assert window._current_topic() == item.text()
    assert window.table.columnCount() == 2
    assert window.table.rowCount() == 1
    assert window.table.item(0, 0).text() == item.text() + " key"


def test_keyboard_topic_selection_exits_search(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.add_topic("beta")
    window = _make_window(qtbot)
    window.search_edit.setText("query")
    qtbot.keyClick(window.topic_list, Qt.Key.Key_Down)
    assert window._current_topic() == "beta"
    assert window.search_edit.text() == ""
    assert data_storage.get_notes_last_search() == ""


@pytest.mark.parametrize("value, expected", [
    (0, 0), (240, 240), (1000, 1000),
    (-1, 120), (1001, 120), ("fast", 120), (None, 120),
    (True, 120), (1.5, 120),
])
def test_fade_duration_config(temp_data_dir, value, expected):
    (temp_data_dir / "config.json").write_text(json.dumps({
        "notes_fade_in_duration_ms": value,
    }))
    assert data_storage.get_notes_fade_in_duration_ms() == expected


def test_fade_in_progresses_and_finishes(qtbot, temp_data_dir):
    window = _make_window(qtbot)
    window.show()
    assert window._fade_in.duration() == 120
    assert window.windowOpacity() == 0.0
    qtbot.waitUntil(lambda: 0.0 < window.windowOpacity() < 1.0)
    # The window remains interactive while fading.
    qtbot.keyClicks(window.search_edit, "query")
    assert window.search_edit.text() == "query"
    qtbot.waitUntil(lambda: window._fade_in.state() == QAbstractAnimation.State.Stopped)
    assert window.windowOpacity() == 1.0


@pytest.mark.parametrize("hide_method", ["hide", "close"])
def test_interrupted_fade_stops_and_reopens(qtbot, temp_data_dir, hide_method):
    window = _make_window(qtbot)
    window.show()
    getattr(window, hide_method)()
    assert window._fade_in.state() == QAbstractAnimation.State.Stopped
    assert window.windowOpacity() == 1.0
    window.show()
    assert window.windowOpacity() == 0.0
    assert window._fade_in.state() == QAbstractAnimation.State.Running
    qtbot.waitUntil(lambda: window._fade_in.state() == QAbstractAnimation.State.Stopped)
    assert window.windowOpacity() == 1.0


def test_fade_config_is_reloaded_and_can_disable_animation(qtbot, temp_data_dir):
    config = temp_data_dir / "config.json"
    config.write_text('{"notes_fade_in_duration_ms": 250}')
    window = _make_window(qtbot)
    window.show()
    assert window._fade_in.duration() == 250
    window.hide()
    config.write_text('{"notes_fade_in_duration_ms": 0}')
    window.show()
    assert window.windowOpacity() == 1.0
    assert window._fade_in.state() == QAbstractAnimation.State.Stopped
