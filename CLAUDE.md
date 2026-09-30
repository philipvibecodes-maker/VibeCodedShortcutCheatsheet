# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Shortcut Cheatsheet is a desktop app that displays keyboard shortcuts for the currently focused application on Ubuntu 24 (Gnome/Wayland) and Windows. It has two windows: a cheatsheet overlay and a settings editor.

## Prerequisites

- Ubuntu 24 with Gnome and Wayland, or Windows 10/11
- On Ubuntu, the "window-calls" Gnome extension must be installed (provides DBus API for window detection on Wayland); Windows needs nothing extra

## Tech Stack

- Python with PyQt6
- Virtual environment at `venv/`
- JSON files for data storage

## Commands

```bash
venv/bin/python main.py          # Run the app
venv/bin/python -m pytest tests/ -v  # Run all tests
```

## Architecture

The codebase should be modular with platform-specific operations isolated for future cross-platform support. Keep these concerns in separate modules:
- **Window detection** — getting the currently focused window (Linux: DBus/window-calls; Windows: Win32 API via ctypes in `src/platform/windows/`)
- **Window movement** — repositioning windows (Linux: standard Qt `move()` under XWayland; Windows: Qt `move()` against `QScreen.availableGeometry()`)
- **Window pinning** — keeping windows above others (Qt `WindowStaysOnTopHint` on both platforms)

## Key Design Decisions

- **XWayland**: The app runs under XWayland, so standard Qt `move()` works for window positioning. The "window-calls" extension is only needed for window detection.
- **Application identification**: Use only the application name (not window title or PID) to identify windows — `wm_class` on Linux, executable name (`notepad.exe`, `Code.exe`) on Windows.
- **Keyboard-first UI**: Everything navigable without a mouse. Use mnemonics, Tab/Shift+Tab navigation, and sensible default keybindings.
- **Cheatsheet window**: Borderless window with rounded corners, dark theme, auto-sizes to fit content (no fixed/minimum dimensions), movable to screen corners with arrow keys, font size adjustable with Ctrl+/Ctrl- and persisted.
- **Settings window**: Opens with `S` key from cheatsheet. Editable shortcut table, app switching menu, add/delete app profiles. All elements focusable and mnemonic-accessible.

## Specs

Detailed specifications live in `specs/`:
- `cheatsheet-specs.md` — Cheatsheet window behavior
- `settings-spec.md` — Settings window behavior
- `window-info-specs.md` — Window detection module
- `style-guidelines.md` — Code organization guidelines
- `tech-stack.md` — Technology choices
