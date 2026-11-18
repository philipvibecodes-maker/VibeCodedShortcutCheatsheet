"""Capture the real NotesWindow with disposable sample data on an X11 desktop.

Usage: QT_QPA_PLATFORM=xcb venv/bin/python tools/review_notes_search.py OUTPUT
"""
import json
import os
import select
import time
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLabel
from src import data_storage as storage
from src.notes.notes_window import NotesWindow

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    storage.get_data_dir = lambda: Path(temporary)
    storage.save_notes_backdrop_opacity(40)
    for topic in ('Git commands', 'Daily notes', 'Project ideas'):
        storage.add_topic(topic)
    storage.add_topic_entry('Git commands', 'Compare to origin main',
        'git fetch origin\ngit diff origin/main...HEAD\n\nReview the changes before opening a pull request.\n'
        'This compares changes on your branch since the common ancestor.\n')
    storage.add_topic_entry('Git commands', 'Review recent commits', 'git log --oneline -10')
    storage.add_topic_entry('Git commands', 'Search commit messages', 'git log --all --grep="search"')
    storage.add_topic_entry('Daily notes', 'Review checklist', 'Read the diff\nRun tests\nCheck the running application\n')
    storage.save_app_shortcuts('Editor', [{'description': 'Search files', 'keys': 'Ctrl+P'}])
    background = QLabel('Notes search review\n\nDisposable sample desktop')
    background.setAlignment(Qt.AlignmentFlag.AlignCenter)
    background.setStyleSheet('background:#20394a;color:#d3dfe7;font-size:28px;')
    background.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.X11BypassWindowManagerHint)
    background.show()
    background.setGeometry(app.primaryScreen().geometry())
    background.raise_()
    QTest.qWait(150)
    window = NotesWindow()
    screen = app.primaryScreen()

    def capture(name):
        QTest.qWait(160)
        assert (window._slide_surface or window).grab().save(str(output / (name + '.png')))

    def record(duration):
        assert not window.isVisible(), "Notes must be hidden before recording"
        background.raise_()
        background.repaint()
        QTest.qWait(150)
        storage.save_notes_fade_in_duration_ms(duration)
        geometry = screen.geometry()
        recording = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'x11grab',
            '-stats_period', '0.05', '-progress', 'pipe:1',
            '-framerate', '60', '-video_size', f'{round(geometry.width() * screen.devicePixelRatio())}x{round(geometry.height() * screen.devicePixelRatio())}',
            '-i', os.environ['DISPLAY'], '-vf', 'scale=1280:-2', '-c:v', 'libx264',
            '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(output / f'opening-{duration}.mp4')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        # Wait for the first captured frame, not an assumed ffmpeg startup time.
        # Otherwise a slow encoder can miss the entire opening animation.
        ready = b""
        deadline = time.monotonic() + 5
        while b"frame=" not in ready and time.monotonic() < deadline:
            if select.select([recording.stdout], [], [], 0)[0]:
                ready += os.read(recording.stdout.fileno(), 4096)
            QTest.qWait(20)
        assert b"frame=" in ready, "Recorder did not capture its first frame"
        QTest.qWait(300)
        window.show()
        window.activateWindow()
        window.search_edit.setFocus()
        QTest.keyClicks(window.search_edit, 'compare', delay=10)
        assert window.search_edit.text() == 'compare'
        QTest.qWait(700)
        recording.communicate(b'q', timeout=10)

    for duration in (0, 120, 180):
        window.search_edit.clear()
        record(duration)
        window.close()
        QTest.qWait(100)
    window.show()
    window.activateWindow()
    window.search_edit.setText('review')
    capture('collapsed-search')
    window.always_topics_action.setChecked(True)
    capture('always-topics-search')
    window.search_edit.clear()
    window.table.setCurrentCell(0, 0)
    capture('full-multiline-values')
    assert window.table.columnCount() == 3
    assert window.table.item(0, 0).text() == 'Git commands'
    assert not window.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable
    assert not hasattr(window, 'preview')
    assert window.table.wordWrap()
    assert window.table.rowHeight(0) > window.table.rowHeight(1)
    original_value = storage.get_topics()['Git commands'][0]['value']
    assert window.table.item(0, 2).text() == original_value
    position = window.table.visualItemRect(window.table.item(0, 1)).center()
    QTest.mouseClick(window.table.viewport(), Qt.MouseButton.LeftButton, pos=position)
    QTest.mouseDClick(window.table.viewport(), Qt.MouseButton.LeftButton, pos=position)
    assert window._active_editor is not None
    QTest.keyClick(window._active_editor[1], Qt.Key.Key_Escape)
    QTest.qWait(30)
    window.table.setCurrentCell(0, 2)
    window.table.setFocus()
    QTest.keyClick(window.table, Qt.Key.Key_Return)
    assert window._active_editor is not None
    window._active_editor[1].setPlainText('git fetch origin\ngit diff origin/main...HEAD\n\nEditing this note inline.')
    capture('inline-edit')
    window._escape()
    QTest.qWait(30)
    assert storage.get_topics()['Git commands'][0]['value'] == original_value
    window.table.setFocus()
    QTest.keyClick(window.table, Qt.Key.Key_C,
                   Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert app.clipboard().text() == original_value
    window.resize(720, 600)
    (window._slide_surface or window).resize(720, 600)
    capture('narrow-always-topics')
    window.always_topics_action.setChecked(False)
    capture('narrow-collapsed')
    window.search_edit.setText('no matching note')
    capture('empty-results')
    window.search_edit.setText('Search files')
    QTest.keyClick(window.search_edit, Qt.Key.Key_Return)
    assert window.table.hasFocus()
    QTest.keyClick(window.table, Qt.Key.Key_Return)
    assert window._active_editor is None
    assert not window.edit_entry_action.isEnabled()
    window._copy_value()
    assert app.clipboard().text() == 'Ctrl+P'
    window.close()
    QTest.qWait(100)
    background.close()
    window.deleteLater()
    QTest.qWait(100)
    app.quit()
print(json.dumps({'screenshots': 7, 'recordings': [0, 120, 180], 'sample_data_only': True}))
