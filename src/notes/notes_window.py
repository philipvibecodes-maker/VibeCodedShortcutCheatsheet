"""Large centered window for recording and searching key/value notes under topics."""

from functools import partial

from PyQt6.QtCore import QEasingCurve, QEvent, QTimeLine, Qt, QTimer
from PyQt6.QtGui import QActionGroup, QColor, QFont, QKeySequence, QPainter, QShortcut
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
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from src.platform import get_focused_window
from src.data_storage import (
    add_topic,
    add_topic_entry,
    delete_topic,
    delete_topic_entry,
    get_all_shortcuts,
    get_notes_fade_in_duration_ms,
    get_notes_animation_strategy,
    get_notes_animation_startup_speed,
    get_notes_font_size,
    get_notes_last_search,
    get_notes_last_topic,
    get_topics,
    save_notes_fade_in_duration_ms,
    save_notes_animation_strategy,
    save_notes_animation_startup_speed,
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
    QMenuBar, QMenu {
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


class _FadeOverlay(QWidget):
    """Reveal live content by fading a dark cover, without native opacity."""

    def __init__(self, parent):
        super().__init__(parent)
        self.progress = 1.0
        self._cover_color = QColor(43, 43, 43)
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


class MultiLineEditDelegate(QStyledItemDelegate):
    """In-place multi-line editor for the value column (Ctrl+Return commits)."""

    def createEditor(self, parent, option, index):
        editor = QPlainTextEdit(parent)
        editor.installEventFilter(self)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        # Rows are ResizeToContents (~1 line for short values); stretch the
        # editor downward over the rows below so multi-line editing is visible.
        rect = option.rect
        wanted = editor.fontMetrics().lineSpacing() * 4 + 12
        if rect.height() < wanted:
            table = self.parent()
            bottom = table.viewport().rect().bottom() if table else rect.bottom()
            rect.setBottom(min(rect.top() + wanted, bottom))
        editor.setGeometry(rect)

    def eventFilter(self, obj, event):
        if (
            isinstance(obj, QPlainTextEdit)
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.commitData.emit(obj)
            self.closeEditor.emit(obj)
            return True
        return super().eventFilter(obj, event)

    def setEditorData(self, editor, index):
        editor.setPlainText(str(index.data() or ""))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText())


class NotesWindow(QMainWindow):
    """Topic/notes browser: search, record, and edit key/value pairs per topic.

    App shortcut profiles are shown as read-only "shortcuts/<app>" topics.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notes")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        # GNOME animates normal windows when mapped. Utility windows appear
        # immediately; this X11 hint also works under XWayland and is ignored
        # on other platforms. Keep the normal Qt title bar and window controls.
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
        self._slide_target = None
        self._fade_in.valueChanged.connect(self._animate_opening)
        self._fade_in.finished.connect(self._finish_opening)
        self.setStyleSheet(DARK_THEME)
        self._font_size = get_notes_font_size()

        notes_menu = self.menuBar().addMenu("&Notes")
        strategy_menu = notes_menu.addMenu("&Animation")
        strategy_group = QActionGroup(self)
        self._strategy_group = strategy_group
        strategy_group.setExclusive(True)
        self.animation_actions = {}
        for strategy, label in (("fade", "&Fade reveal"), ("slide", "&Slide from top")):
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
        layout.addWidget(self.search_edit)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.topic_list = QListWidget()
        self.topic_list.currentItemChanged.connect(self._on_topic_changed)
        # Clicking the current topic should also leave global search results.
        self.topic_list.itemClicked.connect(lambda _item: self.search_edit.clear())
        splitter.addWidget(self.topic_list)

        self.table = QTableWidget()
        self._multiline_delegate = MultiLineEditDelegate(self.table)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setWordWrap(True)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
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
        layout.addLayout(buttons)

        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._change_font_size(1))
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._change_font_size(1))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._change_font_size(-1))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._new_topic)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._new_entry)
        QShortcut(QKeySequence("F2"), self, activated=self._edit_entry)
        QShortcut(QKeySequence("Delete"), self, activated=self._on_delete_key)
        QShortcut(
            QKeySequence("Return"), self.table,
            activated=lambda: self.table.edit(self.table.currentIndex()),
        )

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

    # --- data helpers -----------------------------------------------------

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
            # trailing newlines would make the centered text look top-aligned
            value = value.rstrip("\n")
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
        self.table.setItemDelegateForColumn(0, QStyledItemDelegate(self.table))
        self.table.setItemDelegateForColumn(1, self._multiline_delegate if not searching else QStyledItemDelegate(self.table))
        self.table.setItemDelegateForColumn(value_col, self._multiline_delegate)

        self.table.resizeRowsToContents()

        readonly = self._is_readonly_topic(self._current_topic()) or searching
        self.new_entry_btn.setEnabled(not readonly)
        self.edit_entry_btn.setEnabled(not readonly)
        self.delete_entry_btn.setEnabled(not readonly)
        self.delete_topic_btn.setEnabled(not self._is_readonly_topic(self._current_topic()))

    # --- actions ----------------------------------------------------------

    def _new_topic(self):
        name, ok = QInputDialog.getText(self, "New topic", "Topic name:")
        if ok and add_topic(name):
            self._refresh_topics(select=name.strip())

    def _delete_topic(self):
        topic = self._current_topic()
        if not topic or self._is_readonly_topic(topic):
            return
        answer = QMessageBox.question(
            self, "Delete topic", f"Delete topic '{topic}' and all its entries?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            delete_topic(topic)
            self._refresh_topics()

    def _new_entry(self):
        topic = self._current_topic()
        if not topic or self._is_readonly_topic(topic):
            return
        dialog = EntryDialog(self, title=f"New entry — {topic}")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            key, value = dialog.result()
            if add_topic_entry(topic, key, value):
                self._refresh_topics(select=topic)
                self.table.setCurrentCell(self.table.rowCount() - 1, 0)

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

    def _edit_entry(self):
        topic, index = self._selected_entry()
        if topic is None:
            return
        # open the in-place editor on the key cell of the selected row
        col = 1 if self.table.columnCount() == 3 else 0
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

    def _delete_entry(self):
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
        # Widgets that don't inherit the window font need it set directly
        self.table.horizontalHeader().setFont(font)

    def eventFilter(self, obj, event):
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

    def showEvent(self, event):
        if event.spontaneous():
            super().showEvent(event)
            return
        self._fade_in.stop()
        duration = get_notes_fade_in_duration_ms()
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
        self._fade_overlay.setVisible(bool(duration) and self._animation_strategy == "fade")
        self._fade_overlay.raise_()
        super().showEvent(event)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.7), int(screen.height() * 0.7))
        self.move(
            screen.x() + (screen.width() - self.width()) // 2,
            screen.y() + (screen.height() - self.height()) // 2,
        )
        self._slide_target = self.pos()
        self._slide_start_y = screen.top() - self.frameGeometry().height()
        if duration and self._animation_strategy == "slide":
            self.move(self._slide_target.x(), self._slide_start_y)
        self._fade_overlay.setGeometry(self.rect())
        self.search_edit.setFocus()
        if duration:
            self._fade_in.start()

    def _animate_opening(self, progress):
        if self._animation_strategy == "slide" and self._slide_target is not None:
            y = round(self._slide_start_y +
                      (self._slide_target.y() - self._slide_start_y) * progress)
            self.move(self._slide_target.x(), y)
        else:
            self._fade_overlay.setProgress(progress)

    def _finish_opening(self):
        self._fade_overlay.hide()
        if self._animation_strategy == "slide" and self._slide_target is not None:
            self.move(self._slide_target)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_fade_overlay"):
            self._fade_overlay.setGeometry(self.rect())

    def hideEvent(self, event):
        # Closing/toggling during the fade must leave no running animation.
        self._fade_in.stop()
        self._finish_opening()
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
        if self.isActiveWindow() or QApplication.activeWindow() is not None:
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
