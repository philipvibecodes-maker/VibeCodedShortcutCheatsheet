import sys

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.cheatsheet.cheatsheet_window import CheatsheetWindow
from src.platform.window_detection import is_window_calls_available


def main():
    app = QApplication(sys.argv)

    if not is_window_calls_available():
        msg = QMessageBox(QMessageBox.Icon.Critical, "Missing Extension",
            'The "window-calls" Gnome extension is required but not found.')
        msg.setInformativeText(
            'Install it from:<br>'
            '<a href="https://extensions.gnome.org/extension/4724/window-calls/">'
            'https://extensions.gnome.org/extension/4724/window-calls/</a>'
        )
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.exec()
        sys.exit(1)

    window = CheatsheetWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
