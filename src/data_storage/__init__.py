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


def _get_config_path() -> Path:
    """Return the path to the config.json file."""
    return get_data_dir() / "config.json"


def get_font_size() -> int:
    """Get the stored font size, defaulting to 12."""
    config_path = _get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get("font_size", 12)
        except (json.JSONDecodeError, IOError):
            pass
    return 12


def save_font_size(size: int) -> None:
    """Save font size to config.json, preserving other config values."""
    config_path = _get_config_path()
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    config["font_size"] = size
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def save_app_shortcuts(app_name: str, shortcuts: List[Dict[str, str]]) -> None:
    """
    Save shortcuts for a specific application.

    Args:
        app_name: The application name (e.g., 'brave-browser')
        shortcuts: List of shortcut dicts with 'keys' and 'description' keys.
    """
    data_dir = get_data_dir()
    json_file = data_dir / f"{app_name}.json"

    # Load existing data to preserve display_name
    existing = get_app_shortcuts(app_name)
    display_name = existing["display_name"] if existing else app_name

    data = {
        "app_name": app_name,
        "display_name": display_name,
        "shortcuts": shortcuts,
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)


def delete_app_shortcuts(app_name: str) -> bool:
    """
    Delete the shortcut profile for a specific application.

    Args:
        app_name: The application name (e.g., 'brave-browser')

    Returns:
        True if the file was deleted, False if it didn't exist.
    """
    json_file = get_data_dir() / f"{app_name}.json"
    if json_file.exists():
        json_file.unlink()
        return True
    return False


def has_app_shortcuts(app_name: str) -> bool:
    """Check whether a shortcut profile exists for the given application."""
    json_file = get_data_dir() / f"{app_name}.json"
    return json_file.exists()


def get_tab_profiles(app_name: str) -> List[Dict]:
    """
    Get the tab-specific profiles for an application.

    Tab profiles let one application (e.g. a browser) show different shortcuts
    depending on which tab is focused. Each profile matches a window by a
    case-insensitive substring of its title.

    Returns:
        List of dicts:
        [
            {
                "pattern": str,          # substring matched against the window title
                "display_name": str,
                "shortcuts": [{"keys": str, "description": str}, ...],
            },
            ...
        ]
    """
    data = get_app_shortcuts(app_name)
    if not data:
        return []
    return data.get("tabs", [])


def get_tab_shortcuts(app_name: str, title: str) -> Optional[Dict]:
    """
    Get the tab profile matching a window title, or None.

    The longest matching pattern wins so more specific titles take precedence.
    """
    if not title:
        return None
    best = None
    for tab in get_tab_profiles(app_name):
        pattern = tab.get("pattern", "")
        if pattern and pattern.lower() in title.lower():
            if best is None or len(pattern) > len(best.get("pattern", "")):
                best = tab
    return best


def save_tab_shortcuts(app_name: str, pattern: str, shortcuts: List[Dict[str, str]]) -> None:
    """
    Save shortcuts for a tab profile identified by its title pattern.

    Creates the tab profile (or the app file) when it doesn't exist yet.
    """
    data = get_app_shortcuts(app_name) or {
        "app_name": app_name,
        "display_name": app_name,
        "shortcuts": [],
    }
    tabs = data.setdefault("tabs", [])
    for tab in tabs:
        if tab.get("pattern") == pattern:
            tab["shortcuts"] = shortcuts
            break
    else:
        tabs.append({"pattern": pattern, "display_name": pattern, "shortcuts": shortcuts})

    data_dir = get_data_dir()
    json_file = data_dir / f"{app_name}.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)


def delete_tab_shortcuts(app_name: str, pattern: str) -> bool:
    """Delete the tab profile with the given pattern. Returns True if it existed."""
    data = get_app_shortcuts(app_name)
    if not data:
        return False
    tabs = data.get("tabs", [])
    remaining = [t for t in tabs if t.get("pattern") != pattern]
    if len(remaining) == len(tabs):
        return False
    data["tabs"] = remaining
    json_file = get_data_dir() / f"{app_name}.json"
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    return True


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
