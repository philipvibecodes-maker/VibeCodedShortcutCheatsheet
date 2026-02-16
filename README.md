# Shortcut Cheatsheet

A desktop app that displays keyboard shortcuts for the currently focused application on Ubuntu 24 (Gnome/Wayland). Features a borderless cheatsheet overlay with rounded corners and a settings editor for managing shortcuts.

## Features

- **Auto-updating cheatsheet**: Automatically shows shortcuts for the currently focused application
- **Borderless design**: Modern borderless window with rounded corners and dark theme
- **Font size control**: Adjust font size with Ctrl+ and Ctrl- (8-24pt range)
- **Corner positioning**: Move window to any corner using arrow keys
- **Smart positioning**: Adapts to fullscreen windows by utilizing hidden top bar space
- **Proportional spacing**: All margins, padding, and spacing scale with font size
- **Circular close button**: Custom-painted circular close button in top-right corner
- **Settings window**: Edit shortcuts, add/delete application profiles (press 'S' key)

## Prerequisites

- Ubuntu 24 with Gnome and Wayland
- Python 3.12+
- The **window-calls** Gnome extension (provides DBus API for window detection on Wayland)
  - Install from: https://extensions.gnome.org/extension/4724/window-calls/

## Installation

1. Clone the repository:
```bash
cd ~/personal-utilities
git clone <repository-url> shortcut-cheatsheet-vibed
cd shortcut-cheatsheet-vibed
```

2. Create and activate virtual environment (if not already created):
```bash
python3 -m venv venv
```

3. Install dependencies:
```bash
venv/bin/pip install PyQt6
```

## Running the Application

**Important**: The app must run under XWayland for proper window positioning:

```bash
QT_QPA_PLATFORM=xcb venv/bin/python main.py
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
- **Shortcuts**: Stored in `data/<app_name>.json`
- **Default shortcuts**: Stored in `data/default.json`

## Running Tests

```bash
QT_QPA_PLATFORM=xcb venv/bin/python -m pytest tests/ -v
```

## Development

See `CLAUDE.md` for development guidelines and architectural decisions.

## License

[Add your license here]
