import json
import os
import sys

# Force XWayland so standard Qt move() works for window positioning (Linux only)
if sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.cheatsheet.cheatsheet_window import CheatsheetWindow
from src.platform import get_focused_window, is_platform_supported

SERVER_NAME = "ShortcutCheatsheet"


def get_focused_app_name():
    """Get the currently focused app name, or None."""
    try:
        focused = get_focused_window()
        if focused:
            return focused.get("wm_class")
    except Exception:
        pass
    return None


def try_send_toggle():
    """Try to connect to a running instance and send toggle. Returns True if successful."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        focused_app = get_focused_app_name()
        msg = json.dumps({"action": "toggle", "focused_app": focused_app or ""})
        socket.write(msg.encode())
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True
    return False


def try_send_toggle_notes():
    """Ask a running instance to toggle the notes window. Returns True if it connected."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        socket.write(json.dumps({"action": "toggle_notes"}).encode())
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True
    return False


def _register_notes_hotkey(window):
    """Register the global Ctrl+Shift+\\ notes toggle. Best-effort."""
    try:
        if sys.platform.startswith("linux"):
            from src.platform.linux_gnome.hotkey import register_notes_hotkey
            register_notes_hotkey()
        elif sys.platform == "win32":
            from src.platform.windows.hotkey import install_notes_hotkey
            window._notes_hotkey_filter = install_notes_hotkey(window.toggle_notes)
    except Exception as e:
        print(f"Could not register the notes hotkey: {e}")


def main():
    app = QApplication(sys.argv)
    toggle_notes_flag = "--toggle-notes" in sys.argv

    if toggle_notes_flag and try_send_toggle_notes():
        sys.exit(0)
    if not toggle_notes_flag and try_send_toggle():
        sys.exit(0)

    ok, message = is_platform_supported()
    if not ok:
        msg = QMessageBox(QMessageBox.Icon.Critical, "Platform Not Supported", message)
        msg.exec()
        sys.exit(1)

    # Clean up stale socket from a previous crash
    QLocalServer.removeServer(SERVER_NAME)

    server = QLocalServer()
    server.listen(SERVER_NAME)

    window = CheatsheetWindow()

    def on_new_connection():
        client = server.nextPendingConnection()
        if client:
            client.waitForReadyRead(500)
            data = client.readAll().data().decode()
            client.disconnectFromServer()
            try:
                msg = json.loads(data)
                if msg.get("action") == "toggle":
                    window.handle_second_instance(msg.get("focused_app", ""))
                elif msg.get("action") == "toggle_notes":
                    window.toggle_notes()
            except (json.JSONDecodeError, ValueError):
                pass

    server.newConnection.connect(on_new_connection)

    window.show()
    _register_notes_hotkey(window)
    if toggle_notes_flag:
        window.toggle_notes()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
