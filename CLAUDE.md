# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Shortcut Cheatsheet is a desktop app that displays keyboard shortcuts for the currently focused application on Ubuntu 24 (Gnome/Wayland). It has two windows: a cheatsheet overlay and a settings editor.

## Prerequisites

- Ubuntu 24 with Gnome and Wayland
- The "window-calls" Gnome extension installed (provides DBus API for window info on Wayland)

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
- **Window detection** — getting the currently focused window (via DBus/window-calls)
- **Window movement** — repositioning windows (must use DBus on Wayland, not PyQt's move)
- **Window pinning** — keeping windows above others

## Key Design Decisions

- **Wayland constraint**: Standard PyQt window move doesn't work on Wayland. Use the DBus API from the "window-calls" extension for window positioning.
- **Application identification**: Use only the application name (not window title or PID) to identify windows.
- **Keyboard-first UI**: Everything navigable without a mouse. Use mnemonics, Tab/Shift+Tab navigation, and sensible default keybindings.
- **Cheatsheet window**: Standard (not borderless) window, dark theme, auto-sizes to fit content (no fixed/minimum dimensions), movable to screen corners with arrow keys, font size adjustable with Ctrl+/Ctrl- and persisted.
- **Settings window**: Opens with `S` key from cheatsheet. Editable shortcut table, app switching menu, add/delete app profiles. All elements focusable and mnemonic-accessible.

## Specs

Detailed specifications live in `specs/`:
- `cheatsheet-specs.md` — Cheatsheet window behavior
- `settings-spec.md` — Settings window behavior
- `window-info-specs.md` — Window detection module
- `style-guidelines.md` — Code organization guidelines
- `tech-stack.md` — Technology choices
