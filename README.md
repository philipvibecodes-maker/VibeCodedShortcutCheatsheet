# Shortcut Cheatsheet

A desktop app that displays keyboard shortcuts for the currently focused application on Ubuntu 24 (Gnome/Wayland) and Windows. Features a borderless cheatsheet overlay with rounded corners and a settings editor for managing shortcuts.

## Features

- **Auto-updating cheatsheet**: Automatically shows shortcuts for the currently focused application
- **Running indicator**: A keyboard icon appears in the system tray while the app is running, including when its windows are hidden. On GNOME, AppIndicator/tray support must be enabled for it to appear in the top panel.
- **Borderless design**: Modern borderless window with rounded corners and dark theme
- **Font size control**: Adjust font size with Ctrl+ and Ctrl- (8-24pt range)
- **Corner positioning**: Move window to any corner using arrow keys
- **Smart positioning**: Adapts to fullscreen windows by utilizing hidden top bar space
- **Proportional spacing**: All margins, padding, and spacing scale with font size
- **Circular close button**: Custom-painted circular close button in top-right corner
- **Settings window**: Edit shortcuts, add/delete application profiles (press 'S' key)

## Prerequisites

- Python 3.12+

**Linux:**
- Ubuntu 24 with Gnome and Wayland
- The **window-calls** Gnome extension (provides DBus API for window detection on Wayland)
  - Install from: https://extensions.gnome.org/extension/4724/window-calls/

**Windows:**
- Windows 10/11 or Windows Server 2022+. No extras needed — focused-window detection uses the Win32 API directly and window positioning uses Qt, which handles the taskbar and display scaling automatically.

## Installation

1. Clone the repository:
```bash
cd ~/personal-utilities
git clone <repository-url> shortcut-cheatsheet-vibed
cd shortcut-cheatsheet-vibed
```

2. Create and activate virtual environment (if not already created):
```bash
# Linux
python3 -m venv venv

# Windows
python -m venv venv
```

3. Install dependencies:
```bash
# Linux
venv/bin/pip install PyQt6

# Windows
venv\Scripts\pip install PyQt6
```

## Running the Application

The tray icon includes the running revision number (also shown in its tooltip).
Restart the existing application after updating: another launch forwards to the
running instance and does not reload its code. Delivered changes increment
`APP_REVISION` in `src/version.py`; the first numbered update is revision 1.

```bash
# Linux — the app must run under XWayland for proper window positioning:
QT_QPA_PLATFORM=xcb venv/bin/python main.py

# Windows — no special environment needed:
venv\Scripts\python main.py
```

## Usage

### Keyboard Shortcuts

- **Ctrl+** / **Ctrl-**: Increase/decrease font size
- **Arrow Keys**: Move window to corners (Up/Down for top/bottom, Left/Right for left/right)
- **S**: Open settings window
- **Close button**: Click the red circular button in the top-right corner

### Managing Shortcuts

1. Press **S** to open the settings window
2. Select an application from the dropdown menu
3. Edit existing shortcuts in the table or add new ones
4. Changes are saved automatically

### Adding New Applications

1. Open settings (press **S**)
2. Click "Add Application"
3. Enter the application name and display name
4. Add shortcuts for the new application

## Project Structure

```
shortcut-cheatsheet-vibed/
├── main.py                  # Entry point
├── src/
│   ├── cheatsheet/         # Cheatsheet window implementation
│   ├── settings/           # Settings window implementation
│   ├── platform/           # Platform-specific operations (window detection, movement)
│   └── data_storage/       # JSON data storage utilities
├── data/                   # Shortcut data files (JSON)
├── specs/                  # Detailed specifications
└── venv/                   # Virtual environment
```

## Configuration

- **Font size**: Stored in `data/config.json` (default: 12pt)
- **Notes fade-in**: Open the **Notes** menu in the notes window and adjust the **Fade-in time** slider (0–1000 ms; default: 120). A dark cover fades away inside Qt to reveal the content smoothly, bypassing GNOME's native window-opacity handling. The title bar and dark window surface appear immediately. At 0 the fade is off. Changes save automatically and apply the next time notes opens. You can also set `notes_fade_in_duration_ms` in `data/config.json`. Native GNOME opening animations remain bypassed.
- **Shortcuts**: Stored in `data/<app_name>.json`. The app name is the `wm_class` on Linux (e.g. `brave-browser`) and the executable name on Windows (e.g. `notepad.exe`, `Code.exe`).
- **Default shortcuts**: Stored in `data/default.json`

## Running Tests

```bash
# Linux
QT_QPA_PLATFORM=xcb venv/bin/python -m pytest tests/ -v

# Windows
venv\Scripts\python -m pytest tests/ -v
```

## Development

See `CLAUDE.md` for development guidelines and architectural decisions.

## License

[Add your license here]

Choose **Notes → Animation → Fade reveal** or **Slide from top** in the notes window. The choice is saved as `notes_animation_strategy` (`fade` or `slide`). Both modes use the **Animation duration** slider and apply on the next opening; 0 disables animation. Slide moves the whole window down from above the screen to its centered position.

The Notes menu also has a **Startup speed** control (1–6, default 3). Higher values make either animation progress faster at the start and settle more slowly, while keeping the selected total duration. The setting saves automatically and applies on the next opening. The duration slider ignores arrow keys; drag it with the mouse or use Home/End and Page Up/Page Down.

Starting with revision 2, Slide from top uses a temporary frameless host that bypasses GNOME's window-placement handling. The live notes content slides down from outside the screen. Revision 3 adds a persistent in-app title bar that slides with the content and remains after landing, avoiding a native title-bar pop-in. Drag it to move, double-click to maximize/restore, or use its minimize, maximize, and close buttons. Resize with the bottom-right grip.
