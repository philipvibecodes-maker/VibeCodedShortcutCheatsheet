"""Large centered window for recording and searching key/value notes under topics."""

from functools import partial
import subprocess
import sys

from PyQt6.QtCore import QEasingCurve, QEvent, QPoint, QTimeLine, Qt, QTimer
from PyQt6.QtGui import QActionGroup, QColor, QFont, QKeySequence, QPainter, QRegion, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSizeGrip,
    QSplitter,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from src.platform import get_focused_window
from src.notes.backdrop import NotesBackdrop
from src.data_storage import (
    add_topic,
    add_topic_entry,
    delete_topic,
    delete_topic_entry,
    get_all_shortcuts,
    get_notes_fade_in_duration_ms,
    get_notes_animation_strategy,
    get_notes_animation_startup_speed,
    get_notes_backdrop_opacity,
    get_notes_backdrop_style,
    get_notes_backdrop_fade_duration_ms,
    get_notes_font_size,
    get_notes_last_search,
    get_notes_last_topic,
    get_topics,
    get_notes_always_show_topics,
    save_notes_always_show_topics,
    save_notes_fade_in_duration_ms,
    save_notes_animation_strategy,
    save_notes_animation_startup_speed,
    save_notes_backdrop_opacity,
    save_notes_backdrop_style,
    save_notes_backdrop_fade_duration_ms,
    save_notes_font_size,
    save_notes_last_search,
    save_notes_last_topic,
    update_topic_entry,
)

DARK_THEME = """
    QMainWindow {
        background-color: #2b2b2b;
    }
    QLabel {
        color: #e0e0e0;
    }
    QMenuBar,
    QMenu, QMenu {
        background-color: #2b2b2b;
        color: #e0e0e0;
    }
    QMenuBar::item:selected {
        background-color: #444;
    }
    QLineEdit, QPlainTextEdit {
        background-color: #333;
        color: #e0e0e0;
        border: 1px solid #555;
        padding: 6px 8px;
    }
    QLineEdit:focus, QPlainTextEdit:focus {
        background-color: #4a4a4a;
    }
    QListWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        border: 1px solid #444;
    }
    QListWidget::item:selected {
        background-color: #444;
    }
    QListWidget:focus {
        background-color: #3a3a3a;
    }
    QTableWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        gridline-color: #444;
        selection-background-color: #444;
    }
    QTableWidget::item:focus {
        background-color: #3a3a3a;
    }
    QHeaderView::section {
        background-color: #333;
        color: #e0e0e0;
        padding: 4px;
        border: 1px solid #444;
    }
    QPushButton {
        background-color: #333;
        color: #e0e0e0;
        border: 1px solid #555;
        padding: 6px 16px;
    }
    QPushButton:focus {
        background-color: #4a4a4a;
    }
    QPushButton:hover {
        background-color: #444;
    }
    QPushButton:disabled {
        color: #777;
    }
    QDialog {
        background-color: #2b2b2b;
    }
"""

SHORTCUT_TOPIC_PREFIX = "shortcuts/"


def _fade_easing(progress, startup_speed=3):
    """Move immediately, then settle gently without a slow-start dead zone."""
    return 1.0 - (1.0 - progress) ** startup_speed


# PyQt limits distinct custom easing callbacks; reuse these across openings.
_STARTUP_CURVES = {speed: partial(_fade_easing, startup_speed=speed)
                   for speed in range(1, 7)}


class _DurationSlider(QSlider):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right,
                           Qt.Key.Key_Up, Qt.Key.Key_Down):
            event.accept()
            return
        super().keyPressEvent(event)


class _TitleBar(QWidget):
    """One persistent title bar for both the sliding host and final window."""

    def __init__(self, notes):
        super().__init__(notes)
        self.notes = notes
        self.setMinimumHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 4, 0)
        title = QLabel("Notes")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        layout.addStretch()
        for text, name, callback in (
            ("−", "Minimize", self._minimize),
            ("□", "Maximize or restore", self._toggle_maximized),
            ("×", "Close", notes.close),
        ):
            button = QToolButton(self)
            button.setText(text)
            button.setAccessibleName(name)
            button.setToolTip(name)
            button.setStyleSheet(
                "QToolButton { color: #e0e0e0; background: transparent; border: none; padding: 6px 10px; }"
                "QToolButton:hover { background: #555; }"
            )
            button.clicked.connect(callback)
            layout.addWidget(button)

    def _minimize(self):
        if self.notes._fade_in.state() == QTimeLine.State.Running:
            self.notes._fade_in.stop()
            self.notes._finish_opening()
        if self.notes._slide_surface is not None:
            # Override-redirect surfaces do not have a WM minimize action.
            self.notes.hide()
        else:
            self.notes.showMinimized()

    def _toggle_maximized(self):
        if self.notes._fade_in.state() == QTimeLine.State.Running:
            self.notes._fade_in.stop()
            self.notes._finish_opening()
        surface = self.notes._slide_surface
        if surface is not None:
            previous = getattr(self, "_restore_geometry", None)
            if previous is None:
                self._restore_geometry = surface.geometry()
                surface.setGeometry(surface.screen().availableGeometry())
            else:
                surface.setGeometry(previous)
                self._restore_geometry = None
        elif self.notes.isMaximized():
            self.notes.showNormal()
        else:
            self.notes.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.notes._fade_in.state() == QTimeLine.State.Running:
                self.notes._fade_in.stop()
                self.notes._finish_opening()
            self._drag_offset = event.globalPosition().toPoint() - self.window().pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_offset"):
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class _FadeOverlay(QWidget):
    """Reveal live content by fading a dark cover, without native opacity."""

    def __init__(self, parent):
        super().__init__(parent)
        # Keep the Python owner alive during callbacks from Qt's paint loop.
        self._owner = parent
        self.progress = 1.0
        self._cover_color = QColor(43, 43, 43)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()

    def setProgress(self, progress):
        self.progress = progress
        self._cover_color.setAlpha(round(255 * (1 - progress)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), self._cover_color)
        painter.end()


class EntryDialog(QDialog):
    """Dialog for recording a key -> multi-line text entry."""

    def __init__(self, parent=None, key="", value="", title="Entry"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(parent.styleSheet() if parent else DARK_THEME)
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("&Key:"))
        self.key_edit = QLineEdit(key)
        layout.addWidget(self.key_edit)

        layout.addWidget(QLabel("&Value:"))
        self.value_edit = QPlainTextEdit(value)
        self.value_edit.setMinimumSize(400, 160)
        layout.addWidget(self.value_edit)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("&Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        save_btn = QPushButton("&Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        QWidget.setTabOrder(self.key_edit, self.value_edit)
        QWidget.setTabOrder(self.value_edit, cancel_btn)
        QWidget.setTabOrder(cancel_btn, save_btn)

        # Enter/Return should not accept the dialog from the key field;
        # Ctrl+Return saves from anywhere.
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_save)

    def _on_save(self):
        if not self.key_edit.text().strip():
            return
        self.accept()

    def result(self):
        return self.key_edit.text().strip(), self.value_edit.toPlainText()


class NotesEditDelegate(QStyledItemDelegate):
    """Compact display with explicit, focus-safe key/value editing."""

    def __init__(self, table, notes, multiline=False):
        super().__init__(table)
        self.notes = notes
        self.multiline = multiline

    def displayText(self, value, locale):
        text = str(value).replace("\n", "  ·  ")
        return text[:100] + ("…" if len(text) > 100 else "")

    def createEditor(self, parent, option, index):
        editor = QPlainTextEdit(parent) if self.multiline else QLineEdit(parent)
        self.notes._active_editor = (self, editor, index)
        self.notes.search_edit.setEnabled(False)
        self.notes.topic_list.setEnabled(False)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect
        if self.multiline:
            rect.setHeight(min(130, self.parent().viewport().height() - rect.top()))
        editor.setGeometry(rect)

    def setEditorData(self, editor, index):
        if self.multiline:
            editor.setPlainText(str(index.data() or ""))
        else:
            editor.setText(str(index.data() or ""))

    def valid(self, editor):
        if not self.multiline and not editor.text().strip():
            self.notes.feedback.setText("A note key cannot be empty.")
            editor.setFocus()
            return False
        return True

    def setModelData(self, editor, model, index):
        if self.valid(editor):
            model.setData(index, editor.toPlainText() if self.multiline else editor.text().strip())

    def destroyEditor(self, editor, index):
        if self.notes._active_editor and self.notes._active_editor[1] is editor:
            self.notes._active_editor = None
        if self.notes._active_editor is None:
            self.notes.search_edit.setEnabled(True)
            self.notes.topic_list.setEnabled(True)
        super().destroyEditor(editor, index)

    def eventFilter(self, editor, event):
        if event.type() == QEvent.Type.FocusOut:
            # A temporary app switch must not commit or discard an edit.
            return True
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                return not self.valid(editor) or super().eventFilter(editor, event)
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not self.multiline or event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.notes._commit_editor()
                    return True
                return False
        return super().eventFilter(editor, event)


class NotesWindow(QMainWindow):
    """Topic/notes browser: search, record, and edit key/value pairs per topic.

    App shortcut profiles are shown as read-only "shortcuts/<app>" topics.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notes")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        # GNOME animates normal windows when mapped. Utility windows appear
        # immediately; this X11 hint also works under XWayland and is ignored
        # on other platforms. The in-app title bar also travels with the slide.
        self.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeUtility)
        # Fade a simple painted cover inside Qt; GNOME sees an opaque window.
        self._fade_overlay = _FadeOverlay(self)
        self._fade_in = QTimeLine(120, self)
        # Use a finer cadence than Qt's shared property-animation driver.
        # QTimeLine uses elapsed time, so delayed ticks don't extend the fade.
        self._fade_in.setUpdateInterval(8)
        easing = QEasingCurve()
        easing.setCustomType(_fade_easing)
        self._fade_in.setEasingCurve(easing)
        self._animation_strategy = get_notes_animation_strategy()
        self._slide_surface = None
        self._backdrop = None
        self._backdrop_exclusion = None
        self._opening_progress = 1.0
        self._backdrop_progress = 0.0
        self._backdrop_fade = QTimeLine(320, self)
        self._backdrop_fade.setEasingCurve(QEasingCurve.Type.Linear)
        self._backdrop_fade.valueChanged.connect(self._animate_backdrop)
        self._backdrop_start = QTimer(self)
        self._backdrop_start.setSingleShot(True)
        self._backdrop_start.setInterval(75)
        self._backdrop_start.timeout.connect(self._start_backdrop_fade)
        self.installEventFilter(self)
        self._slide_handoff = False
        self._slide_target = None
        self._fade_in.valueChanged.connect(self._animate_opening)
        self._fade_in.finished.connect(self._finish_opening)
        self.setStyleSheet(DARK_THEME)
        self._font_size = get_notes_font_size()
        self._active_editor = None
        self._session_size = None
        self._preparing_opening = False

        chrome = QWidget(self)
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)
        self.title_bar = _TitleBar(self)
        chrome_layout.addWidget(self.title_bar)
        self._notes_menu_bar = QMenuBar(chrome)
        chrome_layout.addWidget(self._notes_menu_bar)
        self.setMenuWidget(chrome)
        notes_menu = self.menuBar().addMenu("&Notes")
        strategy_menu = notes_menu.addMenu("&Animation")
        strategy_group = QActionGroup(self)
        self._strategy_group = strategy_group
        strategy_group.setExclusive(True)
        self.animation_actions = {}
        for strategy, label in (("fade", "&Fade reveal"), ("slide", "&Slide from top"),
                                ("palette", "&Command palette")):
            action = strategy_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(strategy == self._animation_strategy)
            action.setData(strategy)
            strategy_group.addAction(action)
            self.animation_actions[strategy] = action
        strategy_group.triggered.connect(
            lambda action: save_notes_animation_strategy(action.data())
        )
        fade_controls = QWidget()
        fade_layout = QVBoxLayout(fade_controls)
        self.fade_duration_label = QLabel()
        fade_layout.addWidget(self.fade_duration_label)
        self.fade_duration_slider = _DurationSlider(Qt.Orientation.Horizontal)
        self.fade_duration_slider.setRange(0, 1000)
        self.fade_duration_slider.setSingleStep(10)
        self.fade_duration_slider.setPageStep(100)
        self.fade_duration_slider.setMinimumWidth(240)
        self.fade_duration_slider.setAccessibleName("Animation duration")
        fade_controls.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        fade_controls.setFocusProxy(self.fade_duration_slider)
        self.fade_duration_slider.setToolTip("Applies next time notes opens. 0 disables the animation.")
        # Persist once per drag, while still displaying the time as it moves.
        self.fade_duration_slider.setTracking(False)
        self.fade_duration_slider.sliderMoved.connect(self._update_fade_label)
        self.fade_duration_slider.valueChanged.connect(self._save_fade_duration)
        self.fade_duration_label.setBuddy(self.fade_duration_slider)
        fade_layout.addWidget(self.fade_duration_slider)
        startup_label = QLabel("Startup &speed:")
        fade_layout.addWidget(startup_label)
        self.startup_speed_combo = QComboBox()
        for speed in range(1, 7):
            label = f"{speed}" + (" (linear)" if speed == 1 else " (default)" if speed == 3 else "")
            self.startup_speed_combo.addItem(label, speed)
        self.startup_speed_combo.setCurrentIndex(get_notes_animation_startup_speed() - 1)
        self.startup_speed_combo.setToolTip(
            "Higher values start faster and settle more slowly. Applies next opening."
        )
        self.startup_speed_combo.currentIndexChanged.connect(
            lambda index: save_notes_animation_startup_speed(index + 1)
        )
        startup_label.setBuddy(self.startup_speed_combo)
        fade_layout.addWidget(self.startup_speed_combo)
        style_label = QLabel("&Background style (next opening):")
        fade_layout.addWidget(style_label)
        self.backdrop_style_combo = QComboBox()
        for label, value in (("Dark translucent", "dim"), ("Soft spotlight", "spotlight"),
                             ("Blurred desktop", "blur")):
            self.backdrop_style_combo.addItem(label, value)
        self.backdrop_style_combo.setCurrentIndex(
            self.backdrop_style_combo.findData(get_notes_backdrop_style()))
        self.backdrop_style_combo.setToolTip("Applies next time notes opens. Dark styles need no desktop capture.")
        self.backdrop_style_combo.currentIndexChanged.connect(
            lambda index: save_notes_backdrop_style(self.backdrop_style_combo.itemData(index)))
        style_label.setBuddy(self.backdrop_style_combo)
        fade_layout.addWidget(self.backdrop_style_combo)
        self.backdrop_label = QLabel()
        fade_layout.addWidget(self.backdrop_label)
        self.backdrop_slider = _DurationSlider(Qt.Orientation.Horizontal)
        self.backdrop_slider.setRange(0, 100)
        self.backdrop_slider.setValue(get_notes_backdrop_opacity())
        self.backdrop_slider.setAccessibleName("Background opacity")
        self.backdrop_slider.setTracking(False)
        self.backdrop_slider.valueChanged.connect(self._save_backdrop_opacity)
        self.backdrop_label.setBuddy(self.backdrop_slider)
        self.backdrop_label.setText(f"Background &opacity: {self.backdrop_slider.value()}%")
        fade_layout.addWidget(self.backdrop_slider)
        self.backdrop_fade_label = QLabel()
        fade_layout.addWidget(self.backdrop_fade_label)
        self.backdrop_fade_slider = _DurationSlider(Qt.Orientation.Horizontal)
        self.backdrop_fade_slider.setRange(0, 1000)
        self.backdrop_fade_slider.setSingleStep(20)
        self.backdrop_fade_slider.setPageStep(100)
        self.backdrop_fade_slider.setTracking(False)
        self.backdrop_fade_slider.setAccessibleName("Background fade time")
        self.backdrop_fade_slider.setToolTip("Independent of window motion; applies next opening. 0 disables the background fade.")
        self.backdrop_fade_slider.setValue(get_notes_backdrop_fade_duration_ms())
        self.backdrop_fade_label.setBuddy(self.backdrop_fade_slider)
        self.backdrop_fade_label.setText(f"Background fade &time: {self.backdrop_fade_slider.value()} ms")
        self.backdrop_fade_slider.valueChanged.connect(self._save_backdrop_fade_duration)
        fade_layout.addWidget(self.backdrop_fade_slider)
        fade_action = QWidgetAction(notes_menu)
        fade_action.setDefaultWidget(fade_controls)
        notes_menu.addAction(fade_action)
        notes_menu.aboutToShow.connect(
            lambda: QTimer.singleShot(0, self.fade_duration_slider.setFocus)
        )
        self._sync_fade_controls(get_notes_fade_in_duration_ms())

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search all topics and shortcuts…")
        self.search_edit.textChanged.connect(self._refresh_entries)
        self.search_edit.textChanged.connect(save_notes_last_search)
        self.search_edit.setAccessibleName("Search all topics and shortcuts")
        self.search_edit.setMinimumHeight(42)
        search_row = QHBoxLayout()
        self.topics_btn = QPushButton("Topics")
        self.topics_btn.setCheckable(True)
        self.topics_btn.toggled.connect(self._toggle_topics)
        search_row.addWidget(self.topics_btn)
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)
        layout_menu = notes_menu.addMenu("&Layout")
        self.always_topics_action = layout_menu.addAction("Always show topics")
        self.always_topics_action.setCheckable(True)
        self.always_topics_action.setChecked(get_notes_always_show_topics())
        self.always_topics_action.toggled.connect(self._set_topic_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.topic_list = QListWidget()
        self.topic_list.currentItemChanged.connect(self._on_topic_changed)
        # Clicking the current topic should also leave global search results.
        self.topic_list.itemClicked.connect(lambda _item: self.search_edit.clear())
        splitter.addWidget(self.topic_list)

        self.table = QTableWidget()
        self._multiline_delegate = NotesEditDelegate(self.table, self, multiline=True)
        self._key_delegate = NotesEditDelegate(self.table, self)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setWordWrap(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.currentCellChanged.connect(lambda *_: self._update_preview())

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.result_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.result_splitter.addWidget(self.table)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Full note value")
        self.preview.setPlaceholderText("Select a note to read its full value.")
        self.result_splitter.addWidget(self.preview)
        self.result_splitter.setSizes([480, 480])
        splitter.addWidget(self.result_splitter)
        splitter.setSizes([180, 820])
        splitter.setStretchFactor(1, 1)
        self.topic_list.setVisible(get_notes_always_show_topics())
        self.topics_btn.setChecked(get_notes_always_show_topics())
        self.topics_btn.setVisible(not get_notes_always_show_topics())
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.new_topic_btn = QPushButton("New &topic")
        self.new_topic_btn.clicked.connect(self._new_topic)
        buttons.addWidget(self.new_topic_btn)

        self.delete_topic_btn = QPushButton("&Delete topic")
        self.delete_topic_btn.clicked.connect(self._delete_topic)
        buttons.addWidget(self.delete_topic_btn)

        buttons.addStretch()

        self.new_entry_btn = QPushButton("New e&ntry")
        self.new_entry_btn.clicked.connect(self._new_entry)
        buttons.addWidget(self.new_entry_btn)

        self.edit_entry_btn = QPushButton("Ed&it entry")
        self.edit_entry_btn.clicked.connect(self._edit_entry)
        buttons.addWidget(self.edit_entry_btn)

        self.delete_entry_btn = QPushButton("De&lete entry")
        self.delete_entry_btn.clicked.connect(self._delete_entry)
        buttons.addWidget(self.delete_entry_btn)
        manage = QToolButton()
        manage.setText("Manage")
        manage.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        manage_menu = QMenu(manage)
        for button in (self.new_topic_btn, self.delete_topic_btn, self.new_entry_btn, self.delete_entry_btn):
            button.hide()
            action = manage_menu.addAction(button.text())
            action.triggered.connect(button.click)
            # Keep menu availability synchronized with existing action guards.
            manage_menu.aboutToShow.connect(lambda b=button, a=action: a.setEnabled(b.isEnabled()))
        manage.setMenu(manage_menu)
        buttons.addWidget(manage)
        self.copy_btn = QPushButton("Copy value")
        self.copy_btn.setToolTip("Copy the complete value (Ctrl+Shift+C)")
        self.copy_btn.clicked.connect(self._copy_value)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(QSizeGrip(self))
        self.management = QWidget()
        self.management.setLayout(buttons)
        layout.addWidget(self.management)
        self.feedback = QLabel("↑↓ Select   Double-click / Enter Edit cell   Ctrl+Shift+C Copy   Esc Close")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.setInterval(1600)
        self._feedback_timer.timeout.connect(self._restore_feedback)

        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._change_font_size(1))
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._change_font_size(1))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._change_font_size(-1))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._new_topic)
        QShortcut(QKeySequence("Alt+T"), self, activated=self._new_topic)
        QShortcut(QKeySequence("Alt+N"), self, activated=self._new_entry)
        QShortcut(QKeySequence("Alt+I"), self, activated=self._edit_entry)
        QShortcut(QKeySequence("Alt+D"), self, activated=self._delete_topic)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._new_entry)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self._copy_value)
        QShortcut(QKeySequence("Escape"), self, activated=self._escape)
        self.search_edit.installEventFilter(self)

        self.topic_list.installEventFilter(self)
        self.table.installEventFilter(self)

        self._apply_font_size()
        self._refresh_topics(select=get_notes_last_topic())

        # Restore the last search with the text selected, so the previous
        # filter is visible but typing immediately replaces it.
        last_search = get_notes_last_search()
        if last_search:
            self.search_edit.setText(last_search)
            self.search_edit.selectAll()

    def _toggle_topics(self, checked):
        self.topic_list.setVisible(checked or self.always_topics_action.isChecked())

    def _set_topic_layout(self, always):
        save_notes_always_show_topics(always)
        self.topic_list.setVisible(always)
        self.topics_btn.setVisible(not always)
        self.topics_btn.setChecked(always)

    def _selected_identity(self):
        item = self.table.item(self.table.currentRow(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_value(self):
        identity = self._selected_identity()
        if identity:
            topic, index = identity
            entries = self._all_topics().get(topic, [])
            if index < len(entries):
                return entries[index]["value"]
        return None

    def _update_preview(self):
        if not hasattr(self, "preview"):
            return
        value = self._selected_value()
        self.preview.setPlainText(value if value is not None else "")
        self.preview.setPlaceholderText("No matching notes." if not self.table.rowCount()
                                        else "Select a note to read its full value.")
        self.copy_btn.setEnabled(value is not None)
        topic, _ = self._selected_entry()
        self.edit_entry_btn.setEnabled(topic is not None)
        self.delete_entry_btn.setEnabled(topic is not None)

    def _copy_value(self):
        value = self._selected_value()
        if value is not None:
            QApplication.clipboard().setText(value)
            self.feedback.setText("Value copied.")
            self._feedback_timer.start()

    def _restore_feedback(self):
        self.feedback.setText("↑↓ Select   Double-click / Enter Edit cell   Ctrl+Shift+C Copy   Esc Close")

    def _commit_editor(self):
        if not self._active_editor:
            return True
        delegate, editor, index = self._active_editor
        if not delegate.valid(editor):
            return False
        delegate.setModelData(editor, self.table.model(), index)
        delegate.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)
        self._active_editor = None
        return True

    def _escape(self):
        if self._active_editor:
            delegate, editor, _ = self._active_editor
            delegate.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.RevertModelCache)
            self._active_editor = None
            self.search_edit.setFocus()
        else:
            self.close()

    def _dismiss_from_backdrop(self):
        if not self._active_editor:
            self.close()

    # --- data helpers -----------------------------------------------------

    def menuBar(self):
        return self._notes_menu_bar

    def _shortcut_topics(self):
        """App shortcut profiles exposed as read-only topics."""
        result = {}
        for app_name, data in sorted(get_all_shortcuts().items()):
            entries = [
                {"key": s.get("description", ""), "value": s.get("keys", "")}
                for s in data.get("shortcuts", [])
            ]
            result[SHORTCUT_TOPIC_PREFIX + app_name] = entries
        return result

    def _all_topics(self):
        """User topics first, then read-only shortcut topics."""
        topics = dict(get_topics())
        topics.update(self._shortcut_topics())
        return topics

    def _current_topic(self):
        item = self.topic_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _is_readonly_topic(self, topic):
        return topic is not None and topic.startswith(SHORTCUT_TOPIC_PREFIX)

    # --- UI refresh -------------------------------------------------------

    def _on_topic_changed(self, current, previous):
        if current is not None:
            save_notes_last_topic(current.data(Qt.ItemDataRole.UserRole))
        if self.search_edit.text():
            # textChanged refreshes rows and persists the cleared search.
            self.search_edit.clear()
        else:
            self._refresh_entries()

    def _refresh_topics(self, select=None):
        current = select or self._current_topic()
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        for name in self._all_topics():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            if self._is_readonly_topic(name):
                item.setForeground(Qt.GlobalColor.gray)
            self.topic_list.addItem(item)
            if name == current:
                self.topic_list.setCurrentItem(item)
        if self.topic_list.currentRow() < 0 and self.topic_list.count():
            self.topic_list.setCurrentRow(0)
        self.topic_list.blockSignals(False)
        self._refresh_entries()

    def _refresh_entries(self):
        query = self.search_edit.text().strip().lower()
        searching = bool(query)

        previous = self._selected_identity()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        if searching:
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Topic", "Key", "Value"])
        else:
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Key", "Value"])

        rows = []  # (topic, index_or_None, key, value)
        all_topics = self._all_topics()
        if searching:
            for topic, entries in all_topics.items():
                for i, e in enumerate(entries):
                    if query in topic.lower() or query in e["key"].lower() or query in e["value"].lower():
                        rows.append((topic, i, e["key"], e["value"]))
        else:
            topic = self._current_topic()
            for i, e in enumerate(all_topics.get(topic, [])):
                rows.append((topic, i, e["key"], e["value"]))

        cell_align = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._populating = True
        for row, (topic, index, key, value) in enumerate(rows):
            self.table.insertRow(row)
            # Keep complete values in the model; only the delegate abbreviates display.
            cells = [topic, key, value] if searching else [key, value]
            editable = not self._is_readonly_topic(topic)
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(cell_align)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, (topic, index))
                if not editable or (searching and col == 0):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)
        self._populating = False

        header = self.table.horizontalHeader()
        if searching:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # multi-line editor on the value column (plain default elsewhere)
        value_col = 2 if searching else 1
        self.table.setItemDelegateForColumn(0, self._key_delegate)
        self.table.setItemDelegateForColumn(1, self._multiline_delegate if not searching else self._key_delegate)
        self.table.setItemDelegateForColumn(value_col, self._multiline_delegate)

        self.table.resizeRowsToContents()

        self.table.blockSignals(False)
        selected_row = next((r for r in range(self.table.rowCount())
                             if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == previous), 0)
        if self.table.rowCount():
            self.table.setCurrentCell(selected_row, 0)
        self._update_preview()
        readonly = self._is_readonly_topic(self._current_topic()) or searching
        self.new_entry_btn.setEnabled(not readonly)
        topic, index = self._selected_entry()
        self.edit_entry_btn.setEnabled(topic is not None)
        self.delete_entry_btn.setEnabled(topic is not None)
        self.delete_topic_btn.setEnabled(not self._is_readonly_topic(self._current_topic()))

    # --- actions ----------------------------------------------------------

    def _exec_dialog(self, dialog):
        """Keep modal dialogs above the unmanaged notes host and backdrop."""
        if isinstance(dialog, QMessageBox):
            dialog.setOption(QMessageBox.Option.DontUseNativeDialog, True)
        if self._fade_in.state() == QTimeLine.State.Running:
            self._fade_in.stop()
            self._finish_opening()
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setWindowFlags(dialog.windowFlags()
                              | Qt.WindowType.WindowStaysOnTopHint
                              | Qt.WindowType.X11BypassWindowManagerHint)
        dialog.adjustSize()
        center = self.mapToGlobal(self.rect().center())
        dialog.move(center.x() - dialog.width() // 2,
                    center.y() - dialog.height() // 2)
        dialog.show()
        dialog.move(dialog.pos() + center - dialog.frameGeometry().center())
        dialog.raise_()
        dialog.activateWindow()
        result = dialog.exec()
        if self.isVisible():
            self.raise_()
            self.window().activateWindow()
        return result

    def _new_topic(self):
        if not self._commit_editor():
            return
        dialog = QInputDialog(self)
        dialog.setWindowTitle("New topic")
        dialog.setLabelText("Topic name:")
        accepted = self._exec_dialog(dialog) == QDialog.DialogCode.Accepted
        name = dialog.textValue()
        dialog.deleteLater()
        if accepted and add_topic(name):
            self._refresh_topics(select=name.strip())

    def _delete_topic(self):
        if not self._commit_editor():
            return
        topic = self._current_topic()
        if not topic or self._is_readonly_topic(topic):
            return
        dialog = QMessageBox(QMessageBox.Icon.Question, "Delete topic",
                             f"Delete topic '{topic}' and all its entries?",
                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                             self)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        answer = self._exec_dialog(dialog)
        dialog.deleteLater()
        if answer == QMessageBox.StandardButton.Yes:
            delete_topic(topic)
            self._refresh_topics()

    def _new_entry(self):
        if not self._commit_editor():
            return
        topic = self._current_topic()
        if not topic or self._is_readonly_topic(topic):
            return
        dialog = EntryDialog(self, title=f"New entry — {topic}")
        if self._exec_dialog(dialog) == QDialog.DialogCode.Accepted:
            key, value = dialog.result()
            if add_topic_entry(topic, key, value):
                self._refresh_topics(select=topic)
                self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        dialog.deleteLater()

    def _selected_entry(self):
        row = self.table.currentRow()
        if row < 0:
            return None, None
        item = self.table.item(row, 0)
        if not item:
            return None, None
        topic, index = item.data(Qt.ItemDataRole.UserRole)
        if self._is_readonly_topic(topic):
            return None, None
        return topic, index

    def _edit_value(self):
        if self._active_editor or self._selected_entry()[0] is None:
            return
        self.table.setFocus()
        self.table.edit(self.table.model().index(self.table.currentRow(), self.table.columnCount() - 1))

    def _edit_entry(self):
        if self._active_editor:
            return
        topic, index = self._selected_entry()
        if topic is None:
            return
        # Edit the focused cell; the topic context column is read-only.
        key_col = 1 if self.table.columnCount() == 3 else 0
        col = max(key_col, self.table.currentColumn())
        self.table.setFocus()
        self.table.edit(self.table.model().index(self.table.currentRow(), col))

    def _on_item_changed(self, item):
        """Persist in-place cell edits to topics.json."""
        if getattr(self, "_populating", False):
            return
        data_item = self.table.item(item.row(), 0)
        if not data_item:
            return
        topic, index = data_item.data(Qt.ItemDataRole.UserRole)
        if self._is_readonly_topic(topic):
            return
        if self.table.columnCount() == 3:
            key = self.table.item(item.row(), 1).text()
            value = self.table.item(item.row(), 2).text()
        else:
            key = self.table.item(item.row(), 0).text()
            value = self.table.item(item.row(), 1).text()
        update_topic_entry(topic, index, key, value)
        self.table.resizeRowToContents(item.row())
        self._update_preview()

    def _delete_entry(self):
        if not self._commit_editor():
            return
        topic, index = self._selected_entry()
        if topic is None:
            return
        delete_topic_entry(topic, index)
        self._refresh_topics(select=topic)

    def _on_delete_key(self):
        if self.table.hasFocus():
            self._delete_entry()
        elif self.topic_list.hasFocus():
            self._delete_topic()

    def _change_font_size(self, delta):
        new_size = self._font_size + delta
        if new_size < 8 or new_size > 24:
            return
        self._font_size = new_size
        save_notes_font_size(new_size)
        self._apply_font_size()

    def _apply_font_size(self):
        font = QFont(self.font())
        font.setPointSize(self._font_size)
        self.setFont(font)
        # Styles and the native slide host can break font inheritance. Apply
        # the preference to the whole live interface, including the preview.
        for widget in self.findChildren(QWidget):
            widget.setFont(font)

    def eventFilter(self, obj, event):
        if obj is self or obj is self._slide_surface:
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self._update_backdrop_mask()
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Delete and obj in (self.table, self.topic_list):
            self._on_delete_key()
            return True
        if event.type() == QEvent.Type.KeyPress and obj in (self.search_edit, self.table):
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.table.rowCount():
                    if obj is self.table:
                        self._edit_entry()
                    else:
                        self.preview.setFocus()
                return True
            if obj is self.search_edit and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                row = self.table.currentRow() + (1 if event.key() == Qt.Key.Key_Down else -1)
                if self.table.rowCount():
                    self.table.setCurrentCell(max(0, min(row, self.table.rowCount() - 1)), 0)
                return True
        # Item views consume '/' for their own keyboard search; intercept it
        # to focus the search bar instead.
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Slash
        ):
            self.search_edit.setFocus()
            return True
        # Tab past the last cell / Shift+Tab before the first leaves the table
        if (
            obj is self.table
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab)
        ):
            model = self.table.model()
            last = model.index(model.rowCount() - 1, model.columnCount() - 1)
            first = model.index(0, 0)
            if event.key() == Qt.Key.Key_Tab and self.table.currentIndex() == last:
                self.focusNextPrevChild(True)
                return True
            if event.key() == Qt.Key.Key_Backtab and self.table.currentIndex() == first:
                self.focusNextPrevChild(False)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if (
            event.key() == Qt.Key.Key_Slash
            and not isinstance(self.focusWidget(), (QLineEdit, QPlainTextEdit))
        ):
            self.search_edit.setFocus()
            return
        super().keyPressEvent(event)

    # --- window behavior --------------------------------------------------

    def _update_fade_label(self, duration):
        value = f"{duration} ms" if duration else "Off"
        self.fade_duration_label.setText(f"&Animation duration: {value}")

    def _save_fade_duration(self, duration):
        self._update_fade_label(duration)
        save_notes_fade_in_duration_ms(duration)

    def _sync_fade_controls(self, duration):
        self.fade_duration_slider.blockSignals(True)
        self.fade_duration_slider.setValue(duration)
        self.fade_duration_slider.blockSignals(False)
        self._update_fade_label(duration)

    def raise_(self):
        if self._slide_surface is not None:
            self._slide_surface.raise_()
        else:
            super().raise_()

    def _save_backdrop_opacity(self, opacity):
        save_notes_backdrop_opacity(opacity)
        self.backdrop_label.setText(f"Background &opacity: {opacity}%")
        if self._backdrop is None and opacity and self.isVisible():
            self._create_backdrop()
            self._update_backdrop()
            self._backdrop.show()
            self.raise_()
            self._queue_backdrop_fade()
        self._update_backdrop()

    def _save_backdrop_fade_duration(self, duration):
        save_notes_backdrop_fade_duration_ms(duration)
        self.backdrop_fade_label.setText(f"Background fade &time: {duration} ms")

    def _queue_backdrop_fade(self):
        if self._backdrop is not None:
            self._backdrop_progress = 0.0
            self._update_backdrop()
            self._backdrop_start.start()

    def _start_backdrop_fade(self):
        if self._backdrop is None or not self.isVisible():
            return
        self._update_backdrop_mask()
        self._backdrop.prepareAfterFocus(self._backdrop_exclusion)
        duration = get_notes_backdrop_fade_duration_ms()
        if duration:
            self._backdrop_fade.setDuration(duration)
            self._backdrop_fade.setUpdateInterval(self._fade_in.updateInterval())
            self._backdrop_fade.start()
        else:
            self._animate_backdrop(1.0)

    def _animate_backdrop(self, progress):
        self._backdrop_progress = progress
        self._update_backdrop()

    def _create_backdrop(self):
        if self._backdrop is None and get_notes_backdrop_opacity():
            self._backdrop_exclusion = None
            self._backdrop = NotesBackdrop(self.screen(), self._dismiss_from_backdrop, get_notes_backdrop_style())

    def _update_backdrop(self):
        if self._backdrop is not None:
            self._update_backdrop_mask()
            self._backdrop.setStrength(self._backdrop_progress * self.backdrop_slider.value() / 100)

    def _update_backdrop_mask(self):
        if self._backdrop is not None:
            surface = self._slide_surface or self
            exclusion = surface.rect().translated(
                surface.mapToGlobal(QPoint(0, 0)) - self._backdrop.pos())
            if exclusion != self._backdrop_exclusion:
                self._backdrop_exclusion = exclusion
                self._backdrop.setMask(QRegion(self._backdrop.rect()).subtracted(QRegion(exclusion)))

    def _remove_backdrop(self):
        self._backdrop_start.stop()
        self._backdrop_fade.stop()
        self._backdrop_progress = 0.0
        if self._backdrop is not None:
            self._backdrop.hide()
            self._backdrop.deleteLater()
            self._backdrop = None

    def show(self):
        if not self.isVisible():
            opacity = get_notes_backdrop_opacity()
            self.backdrop_slider.blockSignals(True)
            self.backdrop_slider.setValue(opacity)
            self.backdrop_slider.blockSignals(False)
            self.backdrop_label.setText(f"Background &opacity: {opacity}%")
            self.backdrop_style_combo.blockSignals(True)
            self.backdrop_style_combo.setCurrentIndex(
                self.backdrop_style_combo.findData(get_notes_backdrop_style()))
            self.backdrop_style_combo.blockSignals(False)
            self._opening_progress = 0.0 if get_notes_fade_in_duration_ms() else 1.0
            self._backdrop_progress = 0.0
            fade_duration = get_notes_backdrop_fade_duration_ms()
            self.backdrop_fade_slider.blockSignals(True)
            self.backdrop_fade_slider.setValue(fade_duration)
            self.backdrop_fade_slider.blockSignals(False)
            self.backdrop_fade_label.setText(f"Background fade &time: {fade_duration} ms")
            self._create_backdrop()
            self._update_backdrop()
        if (get_notes_animation_strategy() in ("slide", "palette")
                and get_notes_fade_in_duration_ms() and not self._reduced_motion() and not self.isVisible()):
            self._prepare_opening()
            # An override-redirect surface is not repositioned by GNOME.
            # Host the actual widgets, so typing and editing remain live.
            surface = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                              | Qt.WindowType.WindowStaysOnTopHint
                              | Qt.WindowType.X11BypassWindowManagerHint)
            surface.setWindowTitle(self.windowTitle())
            surface.resize(self.size())
            surface.move(self._slide_target.x(), self._slide_start_y)
            self._slide_surface = surface
            surface.installEventFilter(self)
            self.title_bar._restore_geometry = None
            self._normal_window_flags = self.windowFlags()
            self.setParent(surface, Qt.WindowType.Widget)
            self.move(0, 0)
            surface_layout = QVBoxLayout(surface)
            surface_layout.setContentsMargins(0, 0, 0, 0)
            surface_layout.addWidget(self)
            super().show()
            surface.show()
            self._update_backdrop_mask()
            surface.activateWindow()
            self.search_edit.setFocus()
            self._fade_in.start()
            self._queue_backdrop_fade()
        else:
            super().show()

    def showEvent(self, event):
        if event.spontaneous() or self._slide_surface is not None or self._slide_handoff:
            super().showEvent(event)
            return
        duration = self._prepare_opening()
        super().showEvent(event)
        self.search_edit.setFocus()
        if duration:
            self._fade_in.start()
        self._queue_backdrop_fade()

    def _reduced_motion(self):
        if not hasattr(self, "_system_reduced_motion"):
            reduced = False
            try:
                if sys.platform.startswith("linux"):
                    result = subprocess.run(
                        ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
                        capture_output=True, text=True, timeout=0.3)
                    reduced = result.returncode == 0 and result.stdout.strip() == "false"
                elif sys.platform == "win32":
                    import ctypes
                    enabled = ctypes.c_int(1)
                    if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
                        reduced = not enabled.value
            except (OSError, subprocess.TimeoutExpired):
                pass
            self._system_reduced_motion = reduced
        return self._system_reduced_motion

    def _prepare_opening(self):
        self._fade_in.stop()
        duration = 0 if self._reduced_motion() else get_notes_fade_in_duration_ms()
        speed = get_notes_animation_startup_speed()
        self.startup_speed_combo.blockSignals(True)
        self.startup_speed_combo.setCurrentIndex(speed - 1)
        self.startup_speed_combo.blockSignals(False)
        easing = QEasingCurve()
        easing.setCustomType(_STARTUP_CURVES[speed])
        self._fade_in.setEasingCurve(easing)
        self._animation_strategy = get_notes_animation_strategy()
        self.animation_actions[self._animation_strategy].setChecked(True)
        self._fade_in.setDuration(max(1, duration))
        self._sync_fade_controls(duration)
        self._fade_overlay.setProgress(0.0 if duration else 1.0)
        if duration and self._animation_strategy == "palette":
            # Keep the search and results recognizable on the first frame,
            # rather than briefly presenting an empty dark rectangle.
            self._fade_overlay.setProgress(0.85)
        self._fade_overlay.setVisible(bool(duration) and self._animation_strategy in ("fade", "palette"))
        self._fade_overlay.raise_()
        display = self.screen() or QApplication.primaryScreen()
        screen = display.availableGeometry()
        # Avoid rendering two full-screen frames for each 60 Hz presentation.
        interval = round(1000 / max(30.0, display.refreshRate()))
        self._fade_in.setUpdateInterval(max(8, min(33, interval)))
        self._preparing_opening = True
        size = self._session_size
        width = min(size.width() if size else 1000, max(1, screen.width() - 32))
        height = min(size.height() if size else min(700, int(screen.height() * 0.7)),
                     max(1, screen.height() - 32))
        self.resize(width, height)
        self._preparing_opening = False
        self._slide_target = QPoint(
            screen.x() + (screen.width() - self.width()) // 2,
            screen.y() + (screen.height() - self.height()) // 2,
        )
        # Use the physical screen edge, not the work area below GNOME's bar.
        # Leave a margin for shadows and decorations that arrive during mapping.
        self._slide_start_y = display.geometry().top() - self.frameGeometry().height() - 32
        if self._animation_strategy == "palette":
            # IDE palettes emerge close to their destination, without a long
            # offscreen journey or an opacity request to the compositor.
            self._slide_start_y = self._slide_target.y() - 12
        if duration and self._animation_strategy in ("slide", "palette"):
            self.move(self._slide_target.x(), self._slide_start_y)
        else:
            self.move(self._slide_target)
        self._fade_overlay.setGeometry(self.rect())
        # Prepare the final exclusion before mapping the backdrop. Otherwise
        # a disabled animation can briefly show a hole at the old window position.
        if self._backdrop is not None and not self._backdrop.isVisible():
            self._update_backdrop()
            self._backdrop.show()
        return duration

    def _animate_opening(self, progress):
        self._opening_progress = progress
        if self._animation_strategy in ("slide", "palette") and self._slide_target is not None:
            y = round(self._slide_start_y +
                      (self._slide_target.y() - self._slide_start_y) * progress)
            surface = self._slide_surface or self
            surface.move(self._slide_target.x(), y)
        if self._animation_strategy in ("fade", "palette"):
            # Readable immediately; finish the small brightness change before
            # the last few pixels settle. Avoid a prolonged "disabled" look.
            reveal = progress
            if self._animation_strategy == "palette":
                phase = min(1.0, progress / 0.4)
                reveal = 1.0 - 0.15 * (1.0 - phase) ** 2
            self._fade_overlay.setProgress(reveal)
            if self._animation_strategy == "palette" and reveal >= 1.0:
                self._fade_overlay.hide()
        self._update_backdrop()

    def _finish_opening(self, show_destination=True):
        if show_destination:
            self._opening_progress = 1.0
            self._update_backdrop()
        if self._slide_surface is not None and show_destination:
            # Keep the exact native surface: reparenting/remapping here causes
            # a compositor flash and changes the shadow at the end of the slide.
            self._slide_surface.move(self._slide_target)
            self._fade_overlay.hide()
            return
        if self._slide_surface is not None:
            surface = self._slide_surface
            self._slide_handoff = True
            self.setParent(None, self._normal_window_flags)
            self.move(self._slide_target)
            self._slide_surface = None
            if show_destination:
                super().show()
                self.raise_()
                self.activateWindow()
                self.search_edit.setFocus()
            surface.hide()
            surface.deleteLater()
            self._slide_handoff = False
        self._fade_overlay.hide()
        if self._animation_strategy in ("slide", "palette") and self._slide_target is not None:
            self.move(self._slide_target)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_fade_overlay"):
            self._fade_overlay.setGeometry(self.rect())
        if hasattr(self, "result_splitter"):
            self.result_splitter.setOrientation(Qt.Orientation.Vertical if self.width() < 800
                                                else Qt.Orientation.Horizontal)
        if self.isVisible() and not self._preparing_opening:
            self._session_size = self.size()

    def close(self):
        if not self._commit_editor():
            return False
        if self._slide_surface is not None:
            # Closing a child while reparenting it in closeEvent can remap it
            # as a top-level window. Hide first; hideEvent owns host cleanup.
            self.hide()
            return True
        return super().close()

    def closeEvent(self, event):
        if not self._commit_editor():
            event.ignore()
            return
        self._remove_backdrop()
        if self._slide_surface is not None:
            self._fade_in.stop()
            self._finish_opening(show_destination=False)
        super().closeEvent(event)

    def hideEvent(self, event):
        if self._slide_handoff:
            super().hideEvent(event)
            return
        self._remove_backdrop()
        # Closing/toggling during the fade must leave no running animation.
        self._fade_in.stop()
        self._finish_opening(show_destination=False)
        self._fade_overlay.hide()
        self._fade_overlay.setProgress(1.0)
        super().hideEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            self._unfocused_checks = 0
            QTimer.singleShot(200, self._close_if_unfocused)

    def _close_if_unfocused(self):
        """Close when another app takes focus; survive maximize/move flicker.

        Qt's active-window state can stay unset through XWayland maximize
        transitions, so the OS-level focused window is the source of truth:
        if it still reports our title, we're mid-transition — do nothing.
        """
        if self._active_editor or self.isActiveWindow() or QApplication.activeWindow() is not None:
            return
        try:
            focused = get_focused_window()
        except Exception:
            focused = None
        if focused and focused.get("title") == self.windowTitle():
            return
        self._unfocused_checks += 1
        if self._unfocused_checks < 5:
            QTimer.singleShot(200, self._close_if_unfocused)
        else:
            self.close()
