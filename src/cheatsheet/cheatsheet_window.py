from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.data_storage import get_app_shortcuts, get_default_shortcuts, get_font_size, has_app_shortcuts, save_font_size
from src.platform.window_detection import get_focused_window
from src.platform.window_movement import get_corner_position
from src.settings.settings_window import SettingsWindow

DARK_THEME = """
    QMainWindow {
        background-color: #1a1a1a;
        border-radius: 10px;
    }
    QWidget#central_widget {
        background-color: #1a1a1a;
        border-radius: 10px;
    }
    QLabel {
        color: #e0e0e0;
        background-color: transparent;
    }
"""


class CircularButton(QPushButton):
    """A square button using custom painting."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._size = 16  # Default size in pixels

    def set_size(self, size):
        """Set the size of the square button in pixels."""
        self._size = int(size)
        self.setFixedSize(self._size, self._size)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine color based on state
        if self.isDown():
            color = QColor("#b71c1c")
        elif self.underMouse():
            color = QColor("#f44336")
        else:
            color = QColor("#d32f2f")

        # Draw square
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRect(0, 0, self._size, self._size)

        # Draw text
        painter.setPen(QColor("white"))
        font = QFont("Arial", int(self._size * 0.6), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, self._size, self._size), Qt.AlignmentFlag.AlignCenter, self.text())


class CheatsheetWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shortcut Cheatsheet")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(DARK_THEME)
        self._current_app = None
        self._corner_v = "top"
        self._corner_h = "right"
        self._initial_move_done = False
        self._font_size = get_font_size()
        self._settings_window = None

        self.central = QWidget()
        self.central.setObjectName("central_widget")
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        window_margin = int(self._font_size * 0.4)
        layout.setContentsMargins(window_margin, window_margin, window_margin, window_margin)

        self.close_button = CircularButton("×", self.central)
        self.close_button.set_size(self._font_size * 1.08)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_button.clicked.connect(self.close)
        self.close_button.setToolTip("Close")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout = layout
        layout.addWidget(self.grid_widget)

        # Detect the currently focused app before our window takes focus
        self._started_hidden = False
        try:
            focused = get_focused_window()
            if focused:
                app_name = focused.get("wm_class")
                if app_name:
                    self._current_app = app_name
                    if has_app_shortcuts(app_name):
                        self._display_shortcuts(get_app_shortcuts(app_name))
                    else:
                        self._started_hidden = True
        except Exception:
            self._started_hidden = True
        if self._started_hidden:
            # Display something so the widget is initialized, then hide after show
            self._display_shortcuts(get_default_shortcuts())
            QTimer.singleShot(0, self.hide)

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

        # Skip update when any of our own windows or dialogs are focused
        if QApplication.activeModalWidget():
            return
        our_titles = {self.windowTitle()}
        if self._settings_window:
            our_titles.add(self._settings_window.windowTitle())
        if focused.get("title") in our_titles:
            return

        focused_app = focused.get("wm_class")
        if focused_app == self._current_app:
            return

        self._current_app = focused_app

        if focused_app and has_app_shortcuts(focused_app):
            data = get_app_shortcuts(focused_app)
            if data:
                if self.isHidden():
                    self.show()
                self.raise_()
                self._display_shortcuts(data)
        else:
            self.hide()

    def _display_shortcuts(self, data):
        if not data:
            return

        self._main_layout.removeWidget(self.grid_widget)
        self.grid_widget.setParent(None)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        vertical_spacing = int(self._font_size * 0.2)
        self.grid_layout.setVerticalSpacing(vertical_spacing)
        self.grid_layout.setHorizontalSpacing(0)
        self._main_layout.addWidget(self.grid_widget)

        grid_row = 0
        vertical_padding = int(self._font_size * 0.15)
        horizontal_padding = int(self._font_size * 0.3)
        for i, shortcut in enumerate(data["shortcuts"]):
            desc_label = QLabel(shortcut["description"])
            desc_label.setStyleSheet(f"font-size: {self._font_size}pt; padding: {vertical_padding}px {horizontal_padding}px;")

            keys_label = QLabel(shortcut["keys"])
            keys_label.setStyleSheet(f"font-size: {self._font_size}pt; padding: {vertical_padding}px {horizontal_padding}px;")
            keys_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            self.grid_layout.addWidget(desc_label, grid_row, 0)
            self.grid_layout.addWidget(keys_label, grid_row, 1)
            grid_row += 1

            # Add separator between rows (but not after the last row)
            if i < len(data["shortcuts"]) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.NoFrame)
                separator.setFixedHeight(1)
                separator.setStyleSheet("background-color: #444444;")
                self.grid_layout.addWidget(separator, grid_row, 0, 1, 2)
                grid_row += 1

        self._main_layout.activate()
        self.setFixedSize(self.sizeHint())
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        QTimer.singleShot(50, self._position_close_button)
        QTimer.singleShot(50, self._move_to_corner)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initial_move_done:
            self._initial_move_done = True
            QTimer.singleShot(50, self._position_close_button)
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
        self.close_button.set_size(self._font_size * 1.08)
        vertical_padding = int(self._font_size * 0.15)
        horizontal_padding = int(self._font_size * 0.3)
        vertical_spacing = int(self._font_size * 0.2)
        window_margin = int(self._font_size * 0.4)
        self._main_layout.setContentsMargins(window_margin, window_margin, window_margin, window_margin)
        self.grid_layout.setVerticalSpacing(vertical_spacing)
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel):
                widget.setStyleSheet(f"font-size: {self._font_size}pt; padding: {vertical_padding}px {horizontal_padding}px;")
        self._main_layout.activate()
        self.setFixedSize(self.sizeHint())
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        QTimer.singleShot(50, self._position_close_button)
        QTimer.singleShot(50, self._move_to_corner)

    def _open_settings(self):
        if self._settings_window and self._settings_window.isVisible():
            self._settings_window.raise_()
            self._settings_window.activateWindow()
            return

        self._settings_window = SettingsWindow(app_name=self._current_app or "default")
        self._settings_window.shortcuts_saved.connect(self._on_shortcuts_saved)
        self._settings_window.app_deleted.connect(self._on_app_deleted)
        self._settings_window.show()

    def _on_shortcuts_saved(self, app_name):
        """Refresh the cheatsheet display if the saved app matches the currently displayed app."""
        if app_name == self._current_app:
            data = get_app_shortcuts(app_name)
            if data:
                self._display_shortcuts(data)

    def _on_app_deleted(self, app_name):
        """Minimize the cheatsheet if the deleted app is currently displayed."""
        if app_name == self._current_app:
            self.hide()

    def _move_to_corner(self):
        try:
            pos = get_corner_position(self, self._corner_v, self._corner_h)
            if pos:
                self.move(pos[0], pos[1])
        except Exception:
            pass

    def _position_close_button(self):
        """Position the close button's top-right corner at the window's top-right corner."""
        button_size = self.close_button.width()
        window_width = self.width()
        x = window_width - button_size
        y = 0
        self.close_button.move(int(x), int(y))
        self.close_button.raise_()

    def closeEvent(self, event):
        """Close the settings window when the cheatsheet window is closed."""
        if self._settings_window and self._settings_window.isVisible():
            self._settings_window.close()
        super().closeEvent(event)
