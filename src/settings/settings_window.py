from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


from src.data_storage import delete_app_shortcuts, get_all_shortcuts, get_app_shortcuts, save_app_shortcuts
from src.platform.window_detection import get_open_app_names


class ShortcutTable(QTableWidget):
    """QTableWidget that allows Tab/Shift+Tab to leave the table at cell boundaries."""

    tab_next_widget = None
    tab_prev_widget = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currentCellChanged.connect(self._on_cell_changed)

    def _on_cell_changed(self, row, col, prev_row, prev_col):
        if row >= 0 and col >= 0 and not self.cellWidget(row, col):
            item = self.item(row, col)
            if item:
                self.editItem(item)
                # Deselect text after editor is created
                QTimer.singleShot(0, self._deselect_current_editor)

    def _deselect_current_editor(self):
        """Deselect text in the current cell editor and position cursor at the end."""
        editor = self.findChild(QLineEdit)
        if editor:
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))
            # Install event filter for proper Tab/Shift+Tab navigation
            editor.installEventFilter(self)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.rowCount() == 0:
            return
        if event.reason() == Qt.FocusReason.TabFocusReason:
            self.setCurrentCell(0, 0)
        elif event.reason() == Qt.FocusReason.BacktabFocusReason:
            last_row = self.rowCount() - 1
            last_col = self.columnCount() - 1
            self.setCurrentCell(last_row, last_col)
            w = self.cellWidget(last_row, last_col)
            if w:
                w.setFocus()

    def keyPressEvent(self, event):
        forward = self._tab_direction(event)
        if forward is not None and self._at_boundary(forward):
            self._focus_outside(forward)
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            forward = self._tab_direction(event)
            if forward is not None:
                row, col = self._find_cell_widget(obj)
                # If not found as a cell widget, check if it's a temporary editor
                if row is None and isinstance(obj, QLineEdit):
                    row, col = self.currentRow(), self.currentColumn()
                if row is not None and row >= 0 and col >= 0:
                    if self._at_boundary_cell(row, col, forward):
                        self._focus_outside(forward)
                        return True
                    next_row, next_col = self._next_cell(row, col, forward)
                    self.setCurrentCell(next_row, next_col)
                    w = self.cellWidget(next_row, next_col)
                    if w:
                        w.setFocus()
                    # Don't call setFocus() for regular cells - _on_cell_changed handles it
                    return True
        return super().eventFilter(obj, event)

    def _focus_outside(self, forward):
        target = self.tab_next_widget if forward else self.tab_prev_widget
        if target:
            target.setFocus()
        else:
            QWidget.focusNextPrevChild(self, forward)
        # Clear cell selection after focus has moved (so editor commits first)
        self.setCurrentCell(-1, -1)

    def _tab_direction(self, event):
        if event.key() == Qt.Key.Key_Backtab:
            return False
        if event.key() == Qt.Key.Key_Tab:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                return False
            return True
        return None

    def _at_boundary(self, forward):
        if self.rowCount() == 0:
            return True
        row, col = self.currentRow(), self.currentColumn()
        if row < 0 or col < 0:
            return False
        return self._at_boundary_cell(row, col, forward)

    def _at_boundary_cell(self, row, col, forward):
        if forward:
            return row == self.rowCount() - 1 and col == self.columnCount() - 1
        return row == 0 and col == 0

    def _next_cell(self, row, col, forward):
        if forward:
            col += 1
            if col >= self.columnCount():
                col = 0
                row += 1
        else:
            col -= 1
            if col < 0:
                col = self.columnCount() - 1
                row -= 1
        return row, col

    def _find_cell_widget(self, widget):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                if self.cellWidget(row, col) is widget:
                    return row, col
        return None, None

DARK_THEME = """
    QMainWindow {
        background-color: #2b2b2b;
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
    QPushButton#delete_btn {
        color: #ff4444;
        font-weight: bold;
        padding: 2px 8px;
        border: none;
    }
    QPushButton#delete_btn:focus {
        background-color: #4a4a4a;
    }
    QComboBox {
        background-color: #333;
        color: #e0e0e0;
        border: 1px solid #555;
        padding: 4px 8px;
    }
    QComboBox:focus {
        background-color: #4a4a4a;
    }
    QComboBox QAbstractItemView {
        background-color: #333;
        color: #e0e0e0;
        selection-background-color: #444;
    }
"""


class SettingsWindow(QMainWindow):
    shortcuts_saved = pyqtSignal(str)  # Signal emitted when shortcuts are saved, passes app_name
    app_deleted = pyqtSignal(str)  # Signal emitted when an app is deleted, passes app_name

    def __init__(self, app_name=None):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setStyleSheet(DARK_THEME)
        self._app_name = app_name
        self._new_apps = set()  # Apps added this session, not yet saved

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        app_row = QHBoxLayout()
        self.app_combo = QComboBox()
        self._populate_app_combo()
        self.app_combo.currentIndexChanged.connect(self._on_app_changed)
        app_row.addWidget(self.app_combo, 1)

        self.add_app_btn = QPushButton("Add a&pp")
        self.add_app_btn.clicked.connect(self._show_add_app_menu)
        app_row.addWidget(self.add_app_btn)

        self.delete_app_btn = QPushButton("&Delete app")
        self.delete_app_btn.clicked.connect(self._delete_app)
        app_row.addWidget(self.delete_app_btn)

        layout.addLayout(app_row)

        self.table = ShortcutTable()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.add_shortcut_btn = QPushButton("&Add shortcut")
        self.add_shortcut_btn.clicked.connect(self._add_shortcut)
        layout.addWidget(self.add_shortcut_btn)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("&Cancel")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("&Save and close")
        self.save_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        self.table.tab_next_widget = self.add_shortcut_btn
        self.table.tab_prev_widget = self.delete_app_btn

        QWidget.setTabOrder(self.app_combo, self.add_app_btn)
        QWidget.setTabOrder(self.add_app_btn, self.delete_app_btn)
        QWidget.setTabOrder(self.delete_app_btn, self.table)
        QWidget.setTabOrder(self.table, self.add_shortcut_btn)
        QWidget.setTabOrder(self.add_shortcut_btn, self.cancel_btn)
        QWidget.setTabOrder(self.cancel_btn, self.save_btn)
        self.save_btn.installEventFilter(self)
        self.app_combo.installEventFilter(self)

        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)

        if app_name:
            index = self.app_combo.findData(app_name)
            if index >= 0:
                self.app_combo.setCurrentIndex(index)
            self._load_shortcuts(app_name)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if obj is self.save_btn and event.key() == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.app_combo.setFocus()
                return True
            if obj is self.app_combo and event.key() == Qt.Key.Key_Backtab:
                self.save_btn.setFocus()
                return True
        return super().eventFilter(obj, event)

    def _show_add_app_menu(self):
        existing_apps = set(get_all_shortcuts().keys())
        running_apps = sorted(set(get_open_app_names()) - existing_apps)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #333;
                color: #e0e0e0;
            }
            QMenu::item:selected {
                background-color: #444;
            }
        """)

        if not running_apps:
            action = menu.addAction("No new applications found")
            action.setEnabled(False)
        else:
            for app_name in running_apps:
                menu.addAction(app_name)

        action = menu.exec(self.add_app_btn.mapToGlobal(
            self.add_app_btn.rect().bottomLeft()
        ))
        if action and action.isEnabled():
            self._add_app(action.text())

    def _add_app(self, app_name):
        save_app_shortcuts(app_name, [])
        self._new_apps.add(app_name)
        self.app_combo.addItem(app_name, app_name)
        index = self.app_combo.findData(app_name)
        self.app_combo.setCurrentIndex(index)

    def _delete_app(self):
        if not self._app_name:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Application")
        msg.setText(f"Delete all shortcuts for {self.app_combo.currentText()}?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        deleted_app_name = self._app_name
        self._new_apps.discard(deleted_app_name)
        delete_app_shortcuts(self._app_name)
        self.app_deleted.emit(deleted_app_name)  # Notify that app was deleted
        self.close()

    def _populate_app_combo(self):
        all_shortcuts = get_all_shortcuts()
        for app_name, data in sorted(all_shortcuts.items(), key=lambda x: x[1].get("display_name", x[0])):
            self.app_combo.addItem(data.get("display_name", app_name), app_name)

    def _on_app_changed(self, index):
        if index < 0:
            return
        app_name = self.app_combo.itemData(index)
        if app_name:
            self._load_shortcuts(app_name)

    def _load_shortcuts(self, app_name):
        self._app_name = app_name
        self.table.setRowCount(0)
        data = get_app_shortcuts(app_name)
        if not data:
            return

        shortcuts = data.get("shortcuts", [])
        self.table.setRowCount(len(shortcuts))
        for row, shortcut in enumerate(shortcuts):
            self.table.setItem(row, 0, QTableWidgetItem(shortcut["description"]))
            self.table.setItem(row, 1, QTableWidgetItem(shortcut["keys"]))
            self._add_delete_button(row)

    def _add_delete_button(self, row):
        btn = QPushButton("X")
        btn.setObjectName("delete_btn")
        btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        btn.clicked.connect(lambda checked, r=row: self._delete_row(r))
        self.table.setCellWidget(row, 2, btn)
        btn.installEventFilter(self.table)

    def _add_shortcut(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self._add_delete_button(row)
        # Use setCurrentCell to trigger _on_cell_changed, which installs event filter
        self.table.setCurrentCell(row, 0)

    def _delete_row(self, row):
        self.table.removeRow(row)
        # Reconnect delete buttons with updated row indices
        for r in range(self.table.rowCount()):
            btn = self.table.cellWidget(r, 2)
            if btn:
                btn.clicked.disconnect()
                btn.clicked.connect(lambda checked, row=r: self._delete_row(row))

    def _save_and_close(self):
        # Close any open editor to ensure changes are committed
        self.table.setCurrentCell(-1, -1)

        if not self._app_name:
            self.close()
            return

        shortcuts = []
        for row in range(self.table.rowCount()):
            desc_item = self.table.item(row, 0)
            keys_item = self.table.item(row, 1)
            description = desc_item.text() if desc_item else ""
            keys = keys_item.text() if keys_item else ""
            if description or keys:
                shortcuts.append({"keys": keys, "description": description})

        self._new_apps.discard(self._app_name)  # Mark as saved
        save_app_shortcuts(self._app_name, shortcuts)
        self.shortcuts_saved.emit(self._app_name)  # Notify that shortcuts were saved
        self.close()

    def closeEvent(self, event):
        """Remove unsaved new apps on close."""
        for app_name in self._new_apps:
            delete_app_shortcuts(app_name)
        self._new_apps.clear()
        super().closeEvent(event)
