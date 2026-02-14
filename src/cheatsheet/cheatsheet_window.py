from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QGridLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

from src.data_storage import get_app_shortcuts, get_default_shortcuts
from src.platform.window_detection import get_focused_app_name

DARK_THEME = """
    QMainWindow {
        background-color: #2b2b2b;
    }
    QLabel {
        color: #e0e0e0;
    }
"""


class CheatsheetWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shortcut Cheatsheet")
        self.setStyleSheet(DARK_THEME)
        self._current_app = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.app_label = QLabel()
        self.app_label.setStyleSheet("font-size: 14pt; padding-bottom: 4px;")
        self.app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.app_label)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout = layout
        layout.addWidget(self.grid_widget)

        self._display_shortcuts(get_default_shortcuts())

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll)
        self._poll_timer.start(500)

    def _on_poll(self):
        try:
            focused_app = get_focused_app_name()
        except Exception:
            return

        if focused_app == self._current_app:
            return

        self._current_app = focused_app

        data = None
        if focused_app:
            data = get_app_shortcuts(focused_app)
        if not data:
            data = get_default_shortcuts()

        self._display_shortcuts(data)

    def _display_shortcuts(self, data):
        if not data:
            self.app_label.setText("No shortcuts found")
            return

        self.app_label.setText(data["display_name"])

        self._main_layout.removeWidget(self.grid_widget)
        self.grid_widget.setParent(None)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self.grid_widget)

        for row, shortcut in enumerate(data["shortcuts"]):
            desc_label = QLabel(shortcut["description"])
            desc_label.setStyleSheet("padding: 2px 4px;")

            keys_label = QLabel(shortcut["keys"])
            keys_label.setStyleSheet("padding: 2px 4px;")
            keys_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            self.grid_layout.addWidget(desc_label, row, 0)
            self.grid_layout.addWidget(keys_label, row, 1)

        self._main_layout.activate()
        self.setFixedSize(self.sizeHint())
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
