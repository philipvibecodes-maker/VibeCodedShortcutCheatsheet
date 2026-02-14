from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.data_storage import get_all_shortcuts, get_app_shortcuts, save_app_shortcuts

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
    def __init__(self, app_name=None):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setStyleSheet(DARK_THEME)
        self._app_name = app_name

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.app_combo = QComboBox()
        self._populate_app_combo()
        self.app_combo.currentIndexChanged.connect(self._on_app_changed)
        layout.addWidget(self.app_combo)

        self.table = QTableWidget()
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

        if app_name:
            index = self.app_combo.findData(app_name)
            if index >= 0:
                self.app_combo.setCurrentIndex(index)
            self._load_shortcuts(app_name)

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

    def _add_shortcut(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self._add_delete_button(row)
        self.table.editItem(self.table.item(row, 0))

    def _delete_row(self, row):
        self.table.removeRow(row)
        # Reconnect delete buttons with updated row indices
        for r in range(self.table.rowCount()):
            btn = self.table.cellWidget(r, 2)
            if btn:
                btn.clicked.disconnect()
                btn.clicked.connect(lambda checked, row=r: self._delete_row(row))

    def _save_and_close(self):
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

        save_app_shortcuts(self._app_name, shortcuts)
        self.close()
