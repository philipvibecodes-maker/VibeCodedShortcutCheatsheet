#!/usr/bin/env python3
"""Print shortcuts for the currently focused application every 500ms for 10 seconds."""

import time
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from platform.window_detection import get_focused_app_name
from data_storage import get_app_shortcuts, get_default_shortcuts


def print_shortcuts(app_name, shortcuts_data, is_default=False):
    """Print shortcuts in a formatted way."""
    print(f"\n{'='*60}")
    if is_default:
        print(f"Focused App: {app_name} (showing defaults)")
    else:
        print(f"Focused App: {shortcuts_data.get('display_name', app_name)}")
    print(f"{'='*60}")

    for shortcut in shortcuts_data.get('shortcuts', []):
        keys = shortcut.get('keys', 'N/A')
        desc = shortcut.get('description', 'N/A')
        print(f"  {keys:20} - {desc}")

    print(f"{'='*60}")


def main():
    """Run the monitoring loop."""
    duration = 10  # seconds
    interval = 0.5  # seconds
    iterations = int(duration / interval)

    print(f"Monitoring focused application for {duration} seconds...")
    print(f"Checking every {interval} seconds")

    for i in range(iterations):
        app_name = get_focused_app_name()

        if app_name:
            shortcuts_data = get_app_shortcuts(app_name)

            if shortcuts_data:
                print_shortcuts(app_name, shortcuts_data, is_default=False)
            else:
                # Fall back to default shortcuts
                default_data = get_default_shortcuts()
                if default_data:
                    print_shortcuts(app_name, default_data, is_default=True)
                else:
                    print(f"\n[{i+1}/{iterations}] Focused: {app_name} (no shortcuts available)")
        else:
            # No focused window - show defaults
            default_data = get_default_shortcuts()
            if default_data:
                print_shortcuts("No focused window", default_data, is_default=True)
            else:
                print(f"\n[{i+1}/{iterations}] No focused window (no shortcuts available)")

        if i < iterations - 1:  # Don't sleep after last iteration
            time.sleep(interval)

    print("\nMonitoring complete!")


if __name__ == "__main__":
    main()
