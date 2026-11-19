"""Record notes on a GNOME/X11 desktop using only disposable demo data.

Run with the desired DISPLAY/XAUTHORITY and QT_QPA_PLATFORM=xcb.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import QEvent, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QVBoxLayout, QWidget
from src import data_storage
from src.notes.notes_window import NotesWindow

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--duration', type=int, default=360)
parser.add_argument('--strategy', choices=['fade', 'slide', 'palette'], default='slide')
parser.add_argument('--background', choices=['dim', 'spotlight', 'blur'], default='dim')
parser.add_argument('--focus-chrome', action='store_true', help='Show a background title-color focus indicator')
parser.add_argument('--topic-dialog', action='store_true', help='Open New topic using Alt+T')
parser.add_argument('--menu', action='store_true', help='Show Notes controls in the recording')
parser.add_argument('--theme', choices=['dark', 'light'], default='dark')
parser.add_argument('--opacity', type=int, default=58)
parser.add_argument('--speed', type=int, default=3)
args = parser.parse_args()
if not 0 <= args.opacity <= 100 or not 0 <= args.duration <= 1000 or not 1 <= args.speed <= 6:
    parser.error('opacity must be 0–100, duration 0–1000, and speed 1–6')
args.output.mkdir(parents=True, exist_ok=True)
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
temporary = tempfile.TemporaryDirectory()
data_storage.get_data_dir = lambda: Path(temporary.name)
(Path(temporary.name) / 'config.json').write_text(json.dumps({
    'notes_animation_strategy': args.strategy, 'notes_fade_in_duration_ms': args.duration,
    'notes_animation_startup_speed': args.speed, 'notes_backdrop_opacity': args.opacity,
    'notes_backdrop_style': args.background,
}))
for topic in ('Daily notes', 'Git commands', 'Project ideas'):
    data_storage.add_topic(topic)
    data_storage.add_topic_entry(topic, 'Plan the next step', 'Review the animation and background treatment.')

class FocusPreview(QWidget):
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and hasattr(self, 'focus_banner'):
            active = self.isActiveWindow()
            self.focus_banner.setText('Background application — ' + ('active' if active else 'inactive'))
            self.focus_banner.setStyleSheet(
                'QLabel { padding: 10px; font-size: 20px; color: ' +
                ('#fff; background: #376e9a;' if active else '#b6bec9; background: #242d38;') + ' }')

background = FocusPreview()
background.setStyleSheet('QWidget { background: #18324b; color: #eaf4ff; } QLabel { padding: 30px; border: 1px solid #526c80; background: #25445b; font-size: 24px; }')
if args.theme == 'light':
    background.setStyleSheet('QWidget { background: #f0f3f7; color: #263547; } QLabel { padding: 30px; border: 1px solid #cbd3df; background: #fff; font-size: 24px; }')
layout = QVBoxLayout(background)
if args.focus_chrome:
    background.focus_banner = QLabel('Background application — active')
    background.focus_banner.setStyleSheet('QLabel { padding: 10px; font-size: 20px; color: #fff; background: #376e9a; }')
    layout.addWidget(background.focus_banner)
layout.addWidget(QLabel('Animation review — sample desktop'))
grid = QGridLayout()
for row in range(3):
    for column in range(4):
        grid.addWidget(QLabel(f'Workspace {row * 4 + column + 1}\n\nDocuments and tasks\n\nSample content'), row, column)
layout.addLayout(grid)
background.setWindowTitle("Animation review — background window")
# Cover unrelated desktop content, including other utility windows, throughout
# recording. The optional title-color banner follows real Qt focus events.
background.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                          | Qt.WindowType.WindowStaysOnTopHint
                          | Qt.WindowType.X11BypassWindowManagerHint)
background.showFullScreen()
background.raise_()
background.activateWindow()
window = NotesWindow()
recorder = None
frames = []
background_frames = []
opening_started = None

def trace(progress):
    if opening_started is not None:
        surface = window._slide_surface or window
        frames.append({"ms": round((time.perf_counter() - opening_started) * 1000, 2),
                       "progress": progress, "y": surface.y()})

window._fade_in.valueChanged.connect(trace)

def trace_background(progress):
    if opening_started is not None and window._backdrop is not None:
        background_frames.append({
            "ms": round((time.perf_counter() - opening_started) * 1000, 2),
            "progress": progress, "strength": window._backdrop.strength,
        })

if hasattr(window, '_backdrop_fade'):
    window._backdrop_fade.valueChanged.connect(trace_background)

def begin():
    global recorder
    screen = app.primaryScreen()
    geometry = screen.geometry()
    recorder = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'x11grab',
        '-framerate', '60', '-video_size', f'{round(geometry.width() * screen.devicePixelRatio())}x{round(geometry.height() * screen.devicePixelRatio())}',
        '-i', os.environ['DISPLAY'], '-vf', 'scale=1280:-2', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(args.output / 'opening.mp4')],
        stdin=subprocess.PIPE)
    QTimer.singleShot(500, open_notes)

def open_notes():
    global opening_started
    opening_started = time.perf_counter()
    window.show()
    if args.topic_dialog:
        from PyQt6.QtTest import QTest
        QTimer.singleShot(500, lambda: QTest.keyClick(
            window, Qt.Key.Key_T, Qt.KeyboardModifier.AltModifier))
    if args.menu:
        menu = window.menuBar().actions()[0].menu()
        QTimer.singleShot(500, lambda: menu.popup(
            window.menuBar().mapToGlobal(window.menuBar().rect().bottomLeft())))
    QTimer.singleShot(1600, finish)

def finish():
    if args.topic_dialog and app.activeModalWidget() is not None:
        app.activeModalWidget().reject()
    window.close()
    recorder.communicate(b'q', timeout=10)
    (args.output / 'timing.json').write_text(json.dumps({
        'duration_ms': args.duration, 'startup_speed': args.speed,
        'background': args.background, 'opacity': args.opacity, 'theme': args.theme,
        'frames': frames, 'background_frames': background_frames,
    }, indent=2))
    background.close()
    app.quit()

QTimer.singleShot(600, begin)
QTimer.singleShot(15000, app.quit)
app.exec()
temporary.cleanup()
