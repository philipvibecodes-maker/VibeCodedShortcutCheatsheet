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
    before = notes._selected_identity()
    notes.always_topics_action.setChecked(True)
    assert storage.get_notes_always_show_topics()
    assert notes.topic_list.isVisible()
    assert not notes.topics_btn.isVisible()
    assert notes.search_edit.text() == 'First'
    assert notes._selected_identity() == before
    restored = NotesWindow()
    qtbot.addWidget(restored)
    assert restored.always_topics_action.isChecked()
    notes.always_topics_action.setChecked(False)
    assert not notes.topic_list.isVisible()


def test_search_order_selection_full_values_and_copy(notes, qtbot):
    notes.search_edit.setText('First')
    assert [notes.table.item(r, 1).text() for r in range(2)] == ['First', 'First beta']
    assert notes.table.item(0, 2).text() == 'First line\nSecond line\n'
    notes._copy_value()
    assert QApplication.clipboard().text() == 'First line\nSecond line\n'
    qtbot.keyClick(notes.search_edit, Qt.Key.Key_Down)
    assert notes.table.currentRow() == 1
    notes.search_edit.setText('First ')
    assert notes._selected_identity() == ('beta', 0)
    qtbot.keyClick(notes.search_edit, Qt.Key.Key_Return)
    assert notes.table.hasFocus()
    notes.search_edit.setText('does not exist')
    assert not notes.copy_action.isEnabled()
    assert notes.table.rowCount() == 0
    assert notes.empty_label.isVisible()
    assert 'No matching' in notes.empty_label.text()


def test_inline_edit_cancel_validation_commit_and_focus_safety(notes, qtbot):
    notes._edit_entry()
    delegate, editor, _ = notes._active_editor
    editor.setText('')
    assert not notes._commit_editor()
    assert 'empty' in editor.toolTip()
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
    assert notes.table.item(0, 2).text() == 'Updated\nvalue\n'
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
    assert not notes.edit_entry_action.isEnabled()
    notes._edit_value()
    assert notes._active_editor is None
    notes._copy_value()
    assert QApplication.clipboard().text() == 'Ctrl+F'


def test_resizing_reopening_and_reduced_motion(notes, qtbot):
    notes.resize(720, 480)
    qtbot.wait(10)
    assert not hasattr(notes, "result_splitter")
    assert not hasattr(notes, "preview")
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


def test_double_click_and_enter_edit_focused_cells(notes, qtbot):
    notes.table.setFocus()
    qtbot.keyClicks(notes.table, 'x')
    assert notes._active_editor is None
    item = notes.table.item(0, 1)
    notes.table.setCurrentItem(item)
    position = notes.table.visualItemRect(item).center()
    qtbot.mouseClick(notes.table.viewport(), Qt.MouseButton.LeftButton, pos=position)
    qtbot.mouseDClick(notes.table.viewport(), Qt.MouseButton.LeftButton, pos=position)
    assert notes._active_editor is not None
    _, editor, _ = notes._active_editor
    editor.setText('abc')
    editor.setCursorPosition(1)
    qtbot.keyClick(editor, Qt.Key.Key_Delete)
    assert editor.text() == 'ac'
    assert len(storage.get_topics()['alpha']) == 2
    notes._escape()
    qtbot.wait(10)
    notes.table.setCurrentCell(0, 2)
    qtbot.keyClick(notes.table, Qt.Key.Key_Return)
    assert isinstance(notes._active_editor[1], QPlainTextEdit)
    notes._escape()
    qtbot.wait(10)


def test_edit_action_uses_current_value_cell(notes):
    notes.table.setCurrentCell(0, 2)
    notes.edit_entry_action.trigger()
    assert isinstance(notes._active_editor[1], QPlainTextEdit)


def test_full_multiline_values_remain_visible_when_resized_or_font_changes(notes, qtbot):
    value = 'A long note with more than a hundred characters. ' * 12 + '\nLast line\n'
    storage.update_topic_entry('alpha', 0, 'First', value)
    notes._refresh_entries()
    notes.resize(720, 600)
    qtbot.wait(30)
    item = notes.table.item(0, 2)
    delegate = notes.table.itemDelegateForColumn(2)
    assert delegate.displayText(value, notes.locale()).replace('\u2028', '\n') == value
    assert item.text() == value
    assert notes.table.wordWrap()
    assert notes.table.rowHeight(0) > notes.table.rowHeight(1) * 2
    before = notes.table.rowHeight(0)
    notes._change_font_size(2)
    qtbot.wait(30)
    assert notes.table.font().pointSize() == notes._font_size
    assert notes.table.item(0, 2).text() == value
    assert notes.table.rowHeight(0) >= before



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


def test_topic_column_stays_visible_and_readonly_with_or_without_search(notes):
    for query in ('', 'First', '', 'no match', ''):
        notes.search_edit.setText(query)
        assert notes.table.columnCount() == 3
        assert [notes.table.horizontalHeaderItem(c).text() for c in range(3)] == ['Topic', 'Key', 'Value']
        assert not notes.table.isColumnHidden(0)
        for row in range(notes.table.rowCount()):
            topic_item = notes.table.item(row, 0)
            topic, index = topic_item.data(Qt.ItemDataRole.UserRole)
            assert topic_item.text() == topic
            assert not topic_item.flags() & Qt.ItemFlag.ItemIsEditable
            assert notes.table.item(row, 1).text() == storage.get_topics()[topic][index]['key']
            assert notes.table.item(row, 2).text() == storage.get_topics()[topic][index]['value']


@pytest.mark.parametrize('column,text', [(1, 'Renamed note'), (2, 'Saved on exit\nSecond line\n')])
def test_leaving_cell_saves_edit(notes, qtbot, column, text):
    notes.table.setCurrentCell(0, column)
    notes.table.setFocus()
    qtbot.keyClick(notes.table, Qt.Key.Key_Return)
    _, editor, _ = notes._active_editor
    if column == 1:
        editor.setText(text)
    else:
        editor.setPlainText(text)
    qtbot.mouseClick(notes.search_edit, Qt.MouseButton.LeftButton)
    qtbot.wait(20)
    assert notes._active_editor is None
    assert storage.get_topics()['alpha'][0]['key' if column == 1 else 'value'] == text
    assert notes.table.item(0, column).text() == text


def test_simplified_footer_and_new_topic_button(notes, qtbot, monkeypatch):
    from PyQt6.QtWidgets import QPushButton
    assert notes.new_topic_btn.isVisible()
    assert not hasattr(notes, 'feedback')
    assert not hasattr(notes, 'copy_btn')
    assert not hasattr(notes, 'edit_entry_btn')
    assert not any(b.isVisible() and b.text() in ('Manage', 'Copy value', 'Edit entry')
                   for b in notes.findChildren(QPushButton))
    called = []
    monkeypatch.setattr(notes, '_exec_dialog', lambda dialog: (called.append(dialog.windowTitle()), 0)[1])
    notes.new_topic_btn.click()
    assert called == ['New topic']


def test_leaving_value_for_another_cell_saves(notes, qtbot):
    notes._edit_value()
    notes._active_editor[1].setPlainText('Saved before selecting another row')
    qtbot.wait(20)
    item = notes.table.item(1, 1)
    qtbot.mouseClick(notes.table.viewport(), Qt.MouseButton.LeftButton,
                     pos=notes.table.visualItemRect(item).center())
    qtbot.wait(20)
    assert notes._active_editor is None
    assert storage.get_topics()['alpha'][0]['value'] == 'Saved before selecting another row'
    assert notes.table.item(0, 2).text() == 'Saved before selecting another row'


def test_leaving_value_for_topic_selection_saves_before_refresh(notes, qtbot):
    notes.topics_btn.setChecked(True)
    notes._edit_value()
    notes._active_editor[1].setPlainText('Saved before changing topic')
    qtbot.wait(20)
    item = notes.topic_list.item(1)
    qtbot.mouseClick(notes.topic_list.viewport(), Qt.MouseButton.LeftButton,
                     pos=notes.topic_list.visualItemRect(item).center())
    qtbot.wait(20)
    assert notes._active_editor is None
    assert storage.get_topics()['alpha'][0]['value'] == 'Saved before changing topic'
    assert notes._current_topic() == 'beta'
    assert notes.table.item(0, 0).text() == 'beta'


def test_invalid_key_does_not_overwrite_saved_key_on_exit(notes, qtbot):
    notes._edit_entry()
    editor = notes._active_editor[1]
    editor.setText('')
    qtbot.mouseClick(notes.search_edit, Qt.MouseButton.LeftButton)
    qtbot.wait(20)
    assert storage.get_topics()['alpha'][0]['key'] == 'First'
    assert notes._active_editor is not None
    notes._escape()


@pytest.mark.parametrize('query,selected_topic,expected', [
    ('', 'beta', 'beta'), ('First', 'beta', 'alpha'),
    ('no matches', 'beta', 'beta'), ('   ', 'beta', 'beta'),
])
def test_new_note_topic_prefill(notes, monkeypatch, query, selected_topic, expected):
    notes.topic_list.setCurrentRow(1)
    assert notes._current_topic() == selected_topic
    notes.search_edit.setText(query)
    if notes.table.rowCount() > 1:
        notes.table.setCurrentCell(notes.table.rowCount() - 1, 1)
    inspected = []
    def inspect(dialog):
        inspected.append(dialog.topic_combo.currentText())
        return 0
    monkeypatch.setattr(notes, '_exec_dialog', inspect)
    assert notes.new_note_btn.isVisible()
    notes.new_note_btn.click()
    assert inspected == [expected]


def test_new_note_save_selected_destination_and_cancel(notes, monkeypatch):
    from PyQt6.QtWidgets import QDialog
    notes.search_edit.setText('First')
    before = storage.get_topics()
    monkeypatch.setattr(notes, '_exec_dialog', lambda dialog: QDialog.DialogCode.Rejected)
    notes.new_note_btn.click()
    assert storage.get_topics() == before
    assert notes.search_edit.text() == 'First'
    def save(dialog):
        assert dialog.topic_combo.currentText() == 'alpha'
        dialog.topic_combo.setCurrentText('new topic')
        dialog.key_edit.setText('New note key')
        dialog.value_edit.setPlainText('Full value\nSecond line\n')
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(notes, '_exec_dialog', save)
    notes.new_note_btn.click()
    assert storage.get_topics()['new topic'] == [{'key': 'New note key', 'value': 'Full value\nSecond line\n'}]
    assert notes.search_edit.text() == ''
    assert notes._current_topic() == 'new topic'
    assert notes.table.item(notes.table.currentRow(), 1).text() == 'New note key'


def test_new_note_empty_library_and_readonly_validation(qtbot, tmp_path, monkeypatch):
    from src.notes.notes_window import EntryDialog
    from PyQt6.QtWidgets import QDialog
    monkeypatch.setattr(storage, 'get_data_dir', lambda: tmp_path)
    window = NotesWindow()
    qtbot.addWidget(window)
    assert window._new_note_topic() == ''
    storage.save_app_shortcuts('demo', [{'description': 'Find', 'keys': 'Ctrl+F'}])
    window._refresh_topics()
    window.search_edit.setText('Find')
    assert window._new_note_topic() == 'shortcuts/demo'
    dialog = EntryDialog(window, topic=window._new_note_topic(), topics=storage.get_topics())
    qtbot.addWidget(dialog)
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))
    dialog.key_edit.setText('Key')
    dialog._on_save()
    assert dialog.error_label.text() == 'Choose a writable topic.'
    assert not accepted
    assert storage.get_topics() == {}
    dialog.topic_combo.setCurrentText('')
    dialog._on_save()
    assert dialog.error_label.text() == 'Enter a topic.'
