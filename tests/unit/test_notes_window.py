"""Unit tests for NotesWindow topic selection persistence.

Runs offscreen with data storage redirected to a tmp dir.
"""

import pytest

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
