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
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QVBoxLayout, QWidget
from src import data_storage
from src.notes.notes_window import NotesWindow

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--duration', type=int, default=360)
parser.add_argument('--strategy', choices=['fade', 'slide', 'palette'], default='slide')
parser.add_argument('--speed', type=int, default=3)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
temporary = tempfile.TemporaryDirectory()
data_storage.get_data_dir = lambda: Path(temporary.name)
(Path(temporary.name) / 'config.json').write_text(json.dumps({
    'notes_animation_strategy': args.strategy, 'notes_fade_in_duration_ms': args.duration,
    'notes_animation_startup_speed': args.speed, 'notes_backdrop_opacity': 58,
}))
for topic in ('Daily notes', 'Git commands', 'Project ideas'):
    data_storage.add_topic(topic)
    data_storage.add_topic_entry(topic, 'Plan the next step', 'Review the animation and background treatment.')

background = QWidget()
background.setStyleSheet('QWidget { background: #18324b; color: #eaf4ff; } QLabel { padding: 30px; border: 1px solid #526c80; background: #25445b; font-size: 24px; }')
layout = QVBoxLayout(background)
layout.addWidget(QLabel('Animation review — sample desktop'))
grid = QGridLayout()
for row in range(3):
    for column in range(4):
        grid.addWidget(QLabel(f'Workspace {row * 4 + column + 1}\n\nDocuments and tasks\n\nSample content'), row, column)
layout.addLayout(grid)
background.showFullScreen()
window = NotesWindow()
recorder = None
frames = []
opening_started = None

def trace(progress):
    if opening_started is not None:
        surface = window._slide_surface or window
        frames.append({"ms": round((time.perf_counter() - opening_started) * 1000, 2),
                       "progress": progress, "y": surface.y()})

window._fade_in.valueChanged.connect(trace)

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
    QTimer.singleShot(1600, finish)

def finish():
    window.close()
    recorder.communicate(b'q', timeout=10)
    (args.output / 'timing.json').write_text(json.dumps({
        'duration_ms': args.duration, 'startup_speed': args.speed,
        'frames': frames,
    }, indent=2))
    background.close()
    app.quit()

QTimer.singleShot(600, begin)
QTimer.singleShot(15000, app.quit)
app.exec()
temporary.cleanup()
