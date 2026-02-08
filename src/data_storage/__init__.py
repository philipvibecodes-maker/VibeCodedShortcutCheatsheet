"""Data storage module for managing application shortcuts."""

import json
from pathlib import Path
from typing import Dict, List, Optional


def get_data_dir() -> Path:
    """Return the path to the data directory."""
    return Path(__file__).parent.parent.parent / "data"


def get_app_shortcuts(app_name: str) -> Optional[Dict]:
    """
    Get shortcuts for a specific application.

    Args:
        app_name: The application name (e.g., 'brave-browser', 'dev.zed.Zed')

    Returns:
        Dictionary containing app shortcuts data, or None if not found.
        Format:
        {
            "app_name": str,
            "display_name": str,
            "shortcuts": [
                {"keys": str, "description": str},
                ...
            ]
        }
    """
    data_dir = get_data_dir()
    json_file = data_dir / f"{app_name}.json"

    if not json_file.exists():
        return None

    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading shortcuts for {app_name}: {e}")
        return None


def get_all_shortcuts() -> Dict[str, Dict]:
    """
    Get shortcuts for all applications.

    Returns:
        Dictionary mapping app_name to shortcuts data.
        Format:
        {
            "brave-browser": {
                "app_name": "brave-browser",
                "display_name": "Brave Browser",
                "shortcuts": [...]
            },
            ...
        }
    """
    data_dir = get_data_dir()
    all_shortcuts = {}

    if not data_dir.exists():
        return all_shortcuts

    # Find all JSON files in the data directory
    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                app_name = data.get("app_name")
                if app_name:
                    all_shortcuts[app_name] = data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {json_file.name}: {e}")
            continue

    return all_shortcuts


def get_all_app_names() -> List[str]:
    """
    Get a list of all application names that have shortcuts defined.

    Returns:
        List of application names (e.g., ['brave-browser', 'dev.zed.Zed'])
    """
    all_shortcuts = get_all_shortcuts()
    return list(all_shortcuts.keys())


def get_default_shortcuts() -> Optional[Dict]:
    """
    Get the default Ubuntu shortcuts.

    Returns:
        Dictionary containing default shortcuts data, or None if not found.
        Format:
        {
            "app_name": "default",
            "display_name": "Ubuntu (Default)",
            "shortcuts": [
                {"keys": str, "description": str},
                ...
            ]
        }
    """
    return get_app_shortcuts("default")
