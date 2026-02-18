#!/bin/bash
# XWayland launcher for Neutralino Shortcut Cheatsheet
# This ensures proper window positioning on Wayland

export QT_QPA_PLATFORM=xcb
cd "$(dirname "$0")"

# Use neu run for development (or ./bin/neutralino-linux_x64 for running without rebuild)
neu run
