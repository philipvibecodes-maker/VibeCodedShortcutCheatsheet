"""Unit tests for NotesWindow topic selection persistence.

Runs offscreen with data storage redirected to a tmp dir.
"""

import json

import pytest
from PyQt6.QtCore import QTimeLine, Qt

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
    assert window.windowOpacity() == 1.0
    assert window._fade_overlay.isVisible()
    assert window._fade_overlay.progress == 0.0
    qtbot.waitUntil(lambda: 0.0 < window._fade_overlay.progress < 1.0)
    # The window remains interactive while fading.
    qtbot.keyClicks(window.search_edit, "query")
    assert window.search_edit.text() == "query"
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.NotRunning)
    assert window._fade_overlay.progress == 1.0
    assert not window._fade_overlay.isVisible()


@pytest.mark.parametrize("hide_method", ["hide", "close"])
def test_interrupted_fade_stops_and_reopens(qtbot, temp_data_dir, hide_method):
    window = _make_window(qtbot)
    window.show()
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.Running)
    getattr(window, hide_method)()
    assert window._fade_in.state() == QTimeLine.State.NotRunning
    assert window._fade_overlay.progress == 1.0
    assert not window._fade_overlay.isVisible()
    window.show()
    assert window._fade_overlay.progress == 0.0
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.Running)
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.NotRunning)
    assert window._fade_overlay.progress == 1.0
    assert not window._fade_overlay.isVisible()


@pytest.mark.parametrize("strategy", ["fade", "slide"])
def test_animation_starts_immediately_without_waiting_for_exposure(
        qtbot, temp_data_dir, monkeypatch, strategy):
    data_storage.save_notes_fade_in_duration_ms(1000)
    data_storage.save_notes_animation_strategy(strategy)
    window = _make_window(qtbot)
    window.winId()
    monkeypatch.setattr(window.windowHandle(), "isExposed", lambda: False)
    window.show()
    assert window._fade_in.state() == QTimeLine.State.Running
    qtbot.waitUntil(lambda: window._fade_in.currentTime() > 0)
    if strategy == "slide":
        window.close()
        return
    for elapsed, expected in ((0, 0), (250, 0.15625), (500, 0.5),
                              (750, 0.84375), (1000, 1)):
        window._fade_in.setCurrentTime(elapsed)
        assert window._fade_overlay.progress == pytest.approx(expected, abs=0.005)
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.NotRunning)


def test_hiding_immediately_stops_animation(qtbot, temp_data_dir):
    window = _make_window(qtbot)
    window.show()
    window.hide()
    qtbot.wait(50)
    assert window._fade_in.state() == QTimeLine.State.NotRunning
    assert window._fade_overlay.progress == 1.0
    assert not window._fade_overlay.isVisible()


def test_fade_reveals_rendered_content_without_native_opacity(
        qtbot, temp_data_dir, monkeypatch):
    data_storage.save_notes_fade_in_duration_ms(1000)
    data_storage.add_topic("Example topic")
    window = _make_window(qtbot)

    def reject_native_opacity(_value):
        pytest.fail("The fade must not use compositor window opacity")

    monkeypatch.setattr(window, "setWindowOpacity", reject_native_opacity)
    window.show()
    # Render deterministic frames without advancing the animation's clock.
    covered = window.grab().toImage()
    window._fade_overlay.setProgress(0.5)
    halfway = window.grab().toImage()
    window._fade_overlay.hide()
    revealed = window.grab().toImage()
    changed_pixels = 0
    for y in range(5, covered.height(), 15):
        for x in range(5, covered.width(), 15):
            start = covered.pixelColor(x, y).getRgb()[:3]
            middle = halfway.pixelColor(x, y).getRgb()[:3]
            end = revealed.pixelColor(x, y).getRgb()[:3]
            assert start == (43, 43, 43)
            if start != end:
                changed_pixels += 1
                assert middle == pytest.approx(
                    tuple((a + b) / 2 for a, b in zip(start, end)), abs=2)
    assert changed_pixels > 0
    assert window.windowOpacity() == 1.0
    window.hide()


def test_fade_cover_follows_resize_and_passes_mouse_input(qtbot, temp_data_dir):
    data_storage.add_topic("alpha")
    data_storage.add_topic("beta")
    window = _make_window(qtbot)
    window.show()
    window.resize(600, 400)
    assert window._fade_overlay.geometry() == window.rect()
    item = window.topic_list.item(1)
    position = window.topic_list.viewport().mapTo(
        window, window.topic_list.visualItemRect(item).center())
    assert window.childAt(position) is window.topic_list.viewport()
    qtbot.mouseClick(window.topic_list.viewport(), Qt.MouseButton.LeftButton,
                     pos=window.topic_list.visualItemRect(item).center())
    assert window._current_topic() == "beta"


def test_fade_config_is_reloaded_and_can_disable_animation(qtbot, temp_data_dir):
    config = temp_data_dir / "config.json"
    config.write_text('{"notes_fade_in_duration_ms": 250}')
    window = _make_window(qtbot)
    window.show()
    assert window._fade_in.duration() == 250
    window.hide()
    config.write_text('{"notes_fade_in_duration_ms": 0}')
    window.show()
    assert window._fade_overlay.progress == 1.0
    assert not window._fade_overlay.isVisible()
    assert window._fade_in.state() == QTimeLine.State.NotRunning
    assert window.fade_duration_slider.value() == 0
    assert "Off" in window.fade_duration_label.text()


def test_fade_slider_saves_and_restores_without_overwriting_settings(qtbot, temp_data_dir):
    data_storage.save_notes_last_search("keep this")
    window = _make_window(qtbot)
    assert window.fade_duration_slider.value() == 120
    window.fade_duration_slider.setValue(350)
    assert data_storage.get_notes_fade_in_duration_ms() == 350
    assert data_storage.get_notes_last_search() == "keep this"
    restored = _make_window(qtbot)
    assert restored.fade_duration_slider.value() == 350
    assert "350 ms" in restored.fade_duration_label.text()
    restored.show()
    assert restored._fade_in.duration() == 350


def test_fade_slider_in_notes_menu_supports_keyboard(qtbot, temp_data_dir):
    data_storage.save_notes_fade_in_duration_ms(0)
    window = _make_window(qtbot)
    window.show()
    menu = window.menuBar().actions()[0].menu()
    menu.popup(window.menuBar().mapToGlobal(window.menuBar().rect().bottomLeft()))
    qtbot.waitUntil(lambda: window.fade_duration_slider.hasFocus())
    qtbot.keyClick(window.fade_duration_slider, Qt.Key.Key_Right)
    assert data_storage.get_notes_fade_in_duration_ms() == 10
    assert "10 ms" in window.fade_duration_label.text()
    qtbot.keyClick(window.fade_duration_slider, Qt.Key.Key_End)
    assert data_storage.get_notes_fade_in_duration_ms() == 1000
    qtbot.keyClick(window.fade_duration_slider, Qt.Key.Key_Home)
    assert data_storage.get_notes_fade_in_duration_ms() == 0
    assert "Off" in window.fade_duration_label.text()
    menu.close()


def test_slide_strategy_moves_down_and_persists(qtbot, temp_data_dir):
    window = _make_window(qtbot)
    window.animation_actions['slide'].trigger()
    assert data_storage.get_notes_animation_strategy() == 'slide'
    data_storage.save_notes_fade_in_duration_ms(1000)
    window.show()
    target = window._slide_target
    assert window.y() < target.y()
    assert not window._fade_overlay.isVisible()
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.Running)
    window._fade_in.setCurrentTime(500)
    assert window.y() == round((window._slide_start_y + target.y()) / 2)
    window._fade_in.setCurrentTime(1000)
    qtbot.waitUntil(lambda: window._fade_in.state() == QTimeLine.State.NotRunning)
    assert window.pos() == target
    window.close()
    restored = _make_window(qtbot)
    assert restored.animation_actions['slide'].isChecked()
    restored.animation_actions['fade'].trigger()
    assert data_storage.get_notes_animation_strategy() == 'fade'
