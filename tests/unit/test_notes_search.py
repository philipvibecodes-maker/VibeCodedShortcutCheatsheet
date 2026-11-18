"""Retrieval and explicit editing behavior, independent of legacy animation tests."""
import json

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPlainTextEdit

from src import data_storage as storage
from src.notes.notes_window import NotesWindow


@pytest.fixture
def notes(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'get_data_dir', lambda: tmp_path)
    storage.save_notes_fade_in_duration_ms(0)
    storage.add_topic('alpha')
    storage.add_topic_entry('alpha', 'First', 'First line\nSecond line\n')
    storage.add_topic_entry('alpha', 'Second', 'Other value')
    storage.add_topic('beta')
    storage.add_topic_entry('beta', 'First beta', 'Third value')
    window = NotesWindow()
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    return window


def test_layout_toggle_and_persistence(notes, qtbot):
    assert not notes.topic_list.isVisible()
    notes.topics_btn.click()
    assert notes.topic_list.isVisible()
    assert not storage.get_notes_always_show_topics()
    notes.search_edit.setText('First')
    before = notes.preview.toPlainText()
    notes.always_topics_action.setChecked(True)
    assert storage.get_notes_always_show_topics()
    assert notes.topic_list.isVisible()
    assert not notes.topics_btn.isVisible()
    assert notes.search_edit.text() == 'First'
    assert notes.preview.toPlainText() == before
    restored = NotesWindow()
    qtbot.addWidget(restored)
    assert restored.always_topics_action.isChecked()
    notes.always_topics_action.setChecked(False)
    assert not notes.topic_list.isVisible()


def test_search_order_selection_preview_and_copy(notes, qtbot):
    notes.search_edit.setText('First')
    assert [notes.table.item(r, 1).text() for r in range(2)] == ['First', 'First beta']
    assert notes.preview.toPlainText() == 'First line\nSecond line\n'
    notes._copy_value()
    assert QApplication.clipboard().text() == 'First line\nSecond line\n'
    qtbot.keyClick(notes.search_edit, Qt.Key.Key_Down)
    assert notes.preview.toPlainText() == 'Third value'
    notes.search_edit.setText('First ')
    assert notes._selected_identity() == ('beta', 0)
    qtbot.keyClick(notes.search_edit, Qt.Key.Key_Return)
    assert notes.preview.hasFocus()
    notes.search_edit.setText('does not exist')
    assert not notes.copy_btn.isEnabled()
    assert notes.preview.toPlainText() == ''
    assert 'No matching' in notes.preview.placeholderText()


def test_inline_edit_cancel_validation_commit_and_focus_safety(notes, qtbot):
    notes._edit_entry()
    delegate, editor, _ = notes._active_editor
    editor.setText('')
    assert not notes._commit_editor()
    assert 'empty' in notes.feedback.text()
    notes.close()
    assert notes.isVisible()
    notes._close_if_unfocused()
    notes._dismiss_from_backdrop()
    assert notes.isVisible()
    notes._escape()
    qtbot.wait(10)
    assert storage.get_topics()['alpha'][0]['key'] == 'First'
    assert notes.search_edit.isEnabled()
    notes._edit_value()
    _, editor, _ = notes._active_editor
    assert isinstance(editor, QPlainTextEdit)
    editor.setPlainText('Updated\nvalue\n')
    qtbot.keyClick(editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(10)
    assert notes._active_editor is None
    assert storage.get_topics()['alpha'][0]['value'] == 'Updated\nvalue\n'
    assert notes.preview.toPlainText() == 'Updated\nvalue\n'
    assert notes.search_edit.isEnabled()


def test_escape_key_cancels_editor_then_closes(notes, qtbot):
    notes._edit_entry()
    _, editor, _ = notes._active_editor
    editor.setText('Discard this')
    qtbot.keyClick(editor, Qt.Key.Key_Escape)
    qtbot.wait(10)
    assert notes._active_editor is None
    assert notes.isVisible()
    assert storage.get_topics()['alpha'][0]['key'] == 'First'
    qtbot.keyClick(notes.search_edit, Qt.Key.Key_Escape)
    assert not notes.isVisible()


def test_global_edit_and_readonly_shortcuts(notes, qtbot):
    storage.save_app_shortcuts('demo', [{'description': 'First shortcut', 'keys': 'Ctrl+F'}])
    notes.search_edit.setText('First')
    notes.table.setCurrentCell(1, 1)
    notes._edit_entry()
    notes._active_editor[1].setText('Renamed')
    assert notes._commit_editor()
    qtbot.wait(10)
    assert storage.get_topics()['beta'][0]['key'] == 'Renamed'
    notes.search_edit.setText('shortcut')
    assert not notes.edit_entry_btn.isEnabled()
    assert not notes.edit_value_btn.isEnabled()
    notes._edit_value()
    assert notes._active_editor is None
    notes._copy_value()
    assert QApplication.clipboard().text() == 'Ctrl+F'


def test_resizing_reopening_and_reduced_motion(notes, qtbot):
    notes.resize(720, 480)
    qtbot.wait(10)
    assert notes.result_splitter.orientation() == Qt.Orientation.Vertical
    notes.close()
    notes.show()
    assert notes.width() == 720
    assert notes.height() == 480
    notes.close()
    storage.save_notes_fade_in_duration_ms(180)
    notes._system_reduced_motion = True
    notes.show()
    assert notes._slide_surface is None
    assert notes._fade_in.state() != notes._fade_in.State.Running
    assert not notes._fade_overlay.isVisible()


def test_defaults_and_saved_preferences(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'get_data_dir', lambda: tmp_path)
    assert storage.get_notes_animation_strategy() == 'palette'
    assert storage.get_notes_fade_in_duration_ms() == 180
    assert storage.get_notes_backdrop_opacity() == 40
    config = {'notes_animation_strategy': 'slide', 'notes_fade_in_duration_ms': 470,
              'notes_backdrop_opacity': 60, 'notes_backdrop_style': 'blur'}
    (tmp_path / 'config.json').write_text(json.dumps(config))
    assert storage.get_notes_animation_strategy() == 'slide'
    assert storage.get_notes_fade_in_duration_ms() == 470
    assert storage.get_notes_backdrop_opacity() == 60
    assert storage.get_notes_backdrop_style() == 'blur'


def test_layout_switch_keeps_active_edit_and_close_commits(notes, qtbot):
    notes._edit_entry()
    _, editor, _ = notes._active_editor
    editor.setText('Saved on close')
    notes.always_topics_action.setChecked(True)
    assert notes._active_editor[1] is editor
    assert editor.text() == 'Saved on close'
    notes.close()
    assert not notes.isVisible()
    assert storage.get_topics()['alpha'][0]['key'] == 'Saved on close'


def test_plain_typing_and_double_click_do_not_edit(notes, qtbot):
    notes.table.setFocus()
    qtbot.keyClicks(notes.table, 'x')
    qtbot.mouseDClick(notes.table.viewport(), Qt.MouseButton.LeftButton,
                     pos=notes.table.visualItemRect(notes.table.item(0, 0)).center())
    assert notes._active_editor is None
    notes._edit_entry()
    _, editor, _ = notes._active_editor
    editor.setText('abc')
    editor.setCursorPosition(1)
    qtbot.keyClick(editor, Qt.Key.Key_Delete)
    assert editor.text() == 'ac'
    assert len(storage.get_topics()['alpha']) == 2


def test_font_changes_retain_readable_preview(notes, qtbot):
    original = notes.preview.toPlainText()
    notes._change_font_size(2)
    assert notes.preview.font().pointSize() == notes._font_size
    assert notes.preview.toPlainText() == original


@pytest.mark.parametrize('duration', [0, 120, 180])
def test_palette_close_really_hides_before_reopening(notes, qtbot, duration):
    notes.close()
    storage.save_notes_fade_in_duration_ms(duration)
    notes.show()
    qtbot.wait(250)
    notes.close()
    qtbot.wait(30)
    assert not notes.isVisible()
    notes.search_edit.clear()
    qtbot.wait(30)
    assert not notes.isVisible()
