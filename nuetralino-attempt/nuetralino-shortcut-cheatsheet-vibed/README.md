# Neutralino Shortcut Cheatsheet

A lightweight desktop application that displays keyboard shortcuts for the currently focused application on Ubuntu 24 (Gnome/Wayland). Built with Neutralino.js.

## Features

- **Auto-updating Cheatsheet**: Automatically displays shortcuts for the active application
- **Smart Positioning**: Move to screen corners with arrow keys, adapts to fullscreen apps
- **Customizable Font Size**: Adjust with Ctrl+/Ctrl- (8-24pt range)
- **Settings Editor**: Add/edit shortcuts for any application
- **Persistent Configuration**: Font size and position preferences saved
- **Lightweight**: Uses web technologies (HTML/CSS/JS) with minimal overhead

## Prerequisites

- **Ubuntu 24** with Gnome and Wayland
- **window-calls Gnome extension**: Required for window detection on Wayland
  - Install from: https://extensions.gnome.org/extension/4724/window-calls/
  - Or via: `gnome-extensions install window-calls@domandoman.github.com`
- **Neutralino CLI** (for development): `npm install -g @neutralinojs/neu`

## Running the Application

### Development Mode

```bash
# From project directory
./run.sh
```

Or directly with Neutralino CLI:

```bash
QT_QPA_PLATFORM=xcb neu run
```

### Production Mode

```bash
# Build the application first
neu build

# Run from dist directory
cd dist/nuetralino-shortcut-cheatsheet-vibed
QT_QPA_PLATFORM=xcb ./nuetralino-shortcut-cheatsheet-vibed-linux_x64
```

**Important**: The `QT_QPA_PLATFORM=xcb` environment variable is required to run under XWayland for proper window positioning on Wayland.

## Usage

### Cheatsheet Window

The cheatsheet window appears automatically and updates when you switch applications.

**Keyboard Shortcuts:**
- **Ctrl+Plus/Minus**: Adjust font size (8-24pt)
- **Arrow Keys**: Move to screen corners (Up=top, Down=bottom, Left=left, Right=right)
- **S**: Open settings window
- **Esc**: Close application

### Settings Window

Press **S** in the cheatsheet window to open settings.

**Features:**
- Select application from dropdown
- Add/edit/delete shortcuts in table
- Add new applications from running apps
- Delete applications
- Save and close or Cancel

**Workflow:**
1. Select an application or add a new one
2. Click "Add Shortcut" to add rows
3. Enter description and keyboard keys
4. Click "Delete" on rows to remove them
5. Click "Save and Close" to save changes

## Configuration Files

All configuration is stored in `resources/data/`:

- `config.json`: User preferences (font size, corner position)
- `<app-name>.json`: Shortcut definitions for each application
- `default.json`: Default shortcuts shown when no app-specific shortcuts exist

## Adding Shortcuts for New Applications

### Method 1: Via Settings Window (Recommended)

1. Open the application you want to add shortcuts for
2. Press **S** in the cheatsheet to open settings
3. Click "Add App..." button
4. Select your application from the running apps list
5. Add shortcuts and save

### Method 2: Manual JSON File

Create a new JSON file in `resources/data/` named `<app-name>.json`:

```json
{
  "app_name": "my-app",
  "shortcuts": [
    {
      "description": "Save file",
      "keys": "Ctrl+S"
    },
    {
      "description": "Open file",
      "keys": "Ctrl+O"
    }
  ]
}
```

**Finding Application Name:**
Run this command and look for your app:
```bash
gdbus call --session \
  --dest org.gnome.Shell \
  --object-path /org/gnome/Shell/Extensions/Windows \
  --method org.gnome.Shell.Extensions.Windows.List
```

The `wm_class` field is the application name (normalized to lowercase with special chars removed).

## Architecture

### Cheatsheet Window
- **Borderless**: Rounded corners, transparent background
- **Always on top**: Stays visible over other windows
- **Auto-sizing**: Resizes to fit content
- **Non-resizable**: Fixed size based on content

### Settings Window
- **Normal window**: Standard title bar and controls
- **Not always on top**: Behaves like a regular application window
- **Resizable**: User can adjust window size

### Inter-Window Communication
- Uses Neutralino's Storage API for state sharing
- Settings window sets `refresh-trigger` on save
- Cheatsheet polls for trigger and refreshes data
- `settings-window-open` flag prevents duplicate windows

## File Structure

```
resources/
├── data/                    # JSON configuration files
│   ├── config.json         # User preferences
│   ├── default.json        # Default shortcuts
│   └── *.json              # App-specific shortcuts
├── css/
│   ├── common.css          # Shared dark theme
│   ├── cheatsheet.css      # Cheatsheet styles
│   └── settings.css        # Settings window styles
├── js/
│   ├── cheatsheet/         # Cheatsheet modules
│   │   ├── main.js         # Initialization & polling
│   │   ├── display.js      # Shortcut rendering
│   │   ├── positioning.js  # Corner movement
│   │   └── keyboard.js     # Event handlers
│   ├── settings/           # Settings modules
│   │   ├── main.js         # Initialization
│   │   ├── table.js        # Table management
│   │   ├── app-manager.js  # Add/delete apps
│   │   └── save-handler.js # Save/cancel logic
│   ├── platform/           # Platform-specific
│   │   ├── window-detection.js  # DBus wrapper
│   │   └── window-movement.js   # Positioning logic
│   ├── data/               # Data layer
│   │   ├── storage.js      # File I/O wrapper
│   │   └── config.js       # Config management
│   └── shared/             # Utilities
│       ├── constants.js    # Constants
│       └── utils.js        # Helper functions
├── index.html              # Cheatsheet window
└── settings.html           # Settings window
```

## Development

### Building

```bash
# Build for all platforms
neu build

# Build for distribution
neu build

# Output will be in dist/ directory
```

### Updating Neutralino

```bash
# Update Neutralino binaries and client library
neu update
```

### Debugging

The app runs with `enableInspector: true` in development mode. Right-click and select "Inspect" to open DevTools.

**Console Logs:**
- Cheatsheet initialization and polling
- Window detection and positioning
- Settings window operations
- File I/O operations

## Troubleshooting

### "window-calls extension may not be installed"

**Problem**: The window-calls Gnome extension is not installed or enabled.

**Solution**:
1. Install: `gnome-extensions install window-calls@domandoman.github.com`
2. Enable: `gnome-extensions enable window-calls@domandoman.github.com`
3. Restart Gnome Shell: Alt+F2, type 'r', press Enter

### Window positioning not working

**Problem**: App not running under XWayland.

**Solution**: Always use `QT_QPA_PLATFORM=xcb` when launching:
```bash
QT_QPA_PLATFORM=xcb ./run.sh
```

### Settings window opens multiple times

**Problem**: Storage API state not properly managed.

**Solution**: Restart the application. The app tracks window state via `settings-window-open` flag.

### Cheatsheet not updating

**Problem**: Polling might have stopped or DBus calls failing.

**Solution**:
1. Check console for errors
2. Verify window-calls extension is working
3. Restart the application

## Comparison with PyQt6 Version

### Advantages
- Smaller binary size (~1.7MB vs ~100MB+ with PyQt6)
- Web-based UI (easier to customize with CSS)
- Cross-platform build support
- Faster development iteration

### Trade-offs
- No `WA_ShowWithoutActivating` equivalent (window briefly takes focus)
- DBus calls via subprocess (slightly slower than native Qt)
- Settings window creates new process each time

## License

MIT

## Credits

Built with [Neutralino.js](https://neutralino.js.org/) - A lightweight cross-platform desktop application framework.
