from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QGridLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

from src.data_storage import get_app_shortcuts, get_default_shortcuts, get_font_size, save_font_size
from src.platform.window_detection import get_focused_window
from src.platform.window_movement import get_window_details, get_window_id_by_title, get_work_area, move_window
from src.settings.settings_window import SettingsWindow

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
        self._corner_v = "top"
        self._corner_h = "right"
        self._initial_move_done = False
        self._font_size = get_font_size()
        self._settings_window = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.app_label = QLabel()
        self.app_label.setStyleSheet(f"font-size: {self._font_size + 2}pt; padding-bottom: 4px;")
        self.app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.app_label)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout = layout
        layout.addWidget(self.grid_widget)

        # Detect the currently focused app before our window takes focus
        data = None
        try:
            focused = get_focused_window()
            if focused:
                app_name = focused.get("wm_class")
                if app_name:
                    self._current_app = app_name
                    data = get_app_shortcuts(app_name)
        except Exception:
            pass
        self._display_shortcuts(data or get_default_shortcuts())

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll)
        self._poll_timer.start(500)

    def _on_poll(self):
        try:
            focused = get_focused_window()
        except Exception:
            return

        if not focused:
            return

        # Skip update when any of our own windows are focused
        our_titles = {self.windowTitle()}
        if self._settings_window:
            our_titles.add(self._settings_window.windowTitle())
        if focused.get("title") in our_titles:
            return

        focused_app = focused.get("wm_class")
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
            desc_label.setStyleSheet(f"font-size: {self._font_size}pt; padding: 2px 4px;")

            keys_label = QLabel(shortcut["keys"])
            keys_label.setStyleSheet(f"font-size: {self._font_size}pt; padding: 2px 4px;")
            keys_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            self.grid_layout.addWidget(desc_label, row, 0)
            self.grid_layout.addWidget(keys_label, row, 1)

        self._main_layout.activate()
        self.setFixedSize(self.sizeHint())
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        QTimer.singleShot(50, self._move_to_corner)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_move_done:
            self._initial_move_done = True
            QTimer.singleShot(100, self._move_to_corner)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier

        if ctrl and key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._change_font_size(1)
        elif ctrl and key == Qt.Key.Key_Minus:
            self._change_font_size(-1)
        elif key == Qt.Key.Key_Up:
            self._corner_v = "top"
            self._move_to_corner()
        elif key == Qt.Key.Key_Down:
            self._corner_v = "bottom"
            self._move_to_corner()
        elif key == Qt.Key.Key_Left:
            self._corner_h = "left"
            self._move_to_corner()
        elif key == Qt.Key.Key_Right:
            self._corner_h = "right"
            self._move_to_corner()
        elif key == Qt.Key.Key_S and not ctrl:
            self._open_settings()
        else:
            super().keyPressEvent(event)

    def _change_font_size(self, delta):
        new_size = self._font_size + delta
        if new_size < 8 or new_size > 24:
            return
        self._font_size = new_size
        save_font_size(new_size)
        self._apply_font_size()

    def _apply_font_size(self):
        self.app_label.setStyleSheet(f"font-size: {self._font_size + 2}pt; padding-bottom: 4px;")
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setStyleSheet(f"font-size: {self._font_size}pt; padding: 2px 4px;")
        self._main_layout.activate()
        self.setFixedSize(self.sizeHint())
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        QTimer.singleShot(50, self._move_to_corner)

    def _open_settings(self):
        if self._settings_window and self._settings_window.isVisible():
            self._settings_window.raise_()
            self._settings_window.activateWindow()
            return

        self._settings_window = SettingsWindow(app_name=self._current_app or "default")
        self._settings_window.show()

    def _move_to_corner(self):
        try:
            work_area = get_work_area()
            if not work_area:
                return

            window_id = get_window_id_by_title(self.windowTitle())
            if window_id is None:
                return

            details = get_window_details(window_id)
            win_width = details["width"]
            win_height = details["height"]

            if self._corner_h == "left":
                x = work_area["x"]
            else:
                x = work_area["x"] + work_area["width"] - win_width

            if self._corner_v == "top":
                y = work_area["y"]
            else:
                y = work_area["y"] + work_area["height"] - win_height

            move_window(window_id, x, y)
        except Exception:
            pass
