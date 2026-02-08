#!/usr/bin/env python3
"""Test script for data_storage module."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_storage import get_app_shortcuts, get_all_shortcuts, get_all_app_names, get_default_shortcuts


def main():
    print("Testing data_storage module\n")
    print("=" * 60)

    # Test 1: Get all app names
    print("\n1. All application names:")
    app_names = get_all_app_names()
    for name in sorted(app_names):
        print(f"   - {name}")

    # Test 2: Get all shortcuts
    print("\n2. All shortcuts:")
    all_shortcuts = get_all_shortcuts()
    print(f"   Found {len(all_shortcuts)} applications with shortcuts")

    # Test 3: Get shortcuts for specific apps
    print("\n3. Specific application shortcuts:\n")

    for app_name in ["brave-browser", "dev.zed.Zed", "gnome-terminal-server"]:
        shortcuts = get_app_shortcuts(app_name)
        if shortcuts:
            print(f"   {shortcuts['display_name']}:")
            for sc in shortcuts['shortcuts']:
                print(f"      {sc['keys']:20} - {sc['description']}")
            print()
        else:
            print(f"   {app_name}: No shortcuts found\n")

    # Test 4: Test default shortcuts
    print("4. Default Ubuntu shortcuts:")
    defaults = get_default_shortcuts()
    if defaults:
        print(f"   {defaults['display_name']}:")
        for sc in defaults['shortcuts']:
            print(f"      {sc['keys']:20} - {sc['description']}")
        print()
    else:
        print("   No default shortcuts found\n")

    # Test 5: Test non-existent app
    print("5. Non-existent application:")
    result = get_app_shortcuts("non-existent-app")
    print(f"   Result: {result}")

    print("\n" + "=" * 60)
    print("Testing complete!")


if __name__ == "__main__":
    main()
