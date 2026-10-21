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


def _get_config() -> Dict:
    config_path = _get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_config_value(key: str, value) -> None:
    config_path = _get_config_path()
    config = _get_config()
    config[key] = value
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def get_font_size() -> int:
    """Get the stored cheatsheet font size, defaulting to 12."""
    return _get_config().get("font_size", 12)


def save_font_size(size: int) -> None:
    """Save the cheatsheet font size to config.json, preserving other values."""
    _save_config_value("font_size", size)


def get_notes_font_size() -> int:
    """Get the stored notes-window font size, defaulting to 12."""
    return _get_config().get("notes_font_size", 12)


def save_notes_font_size(size: int) -> None:
    """Save the notes-window font size to config.json, preserving other values."""
    _save_config_value("notes_font_size", size)


def get_notes_last_topic() -> Optional[str]:
    """Get the topic the notes window last showed, or None if never set."""
    return _get_config().get("notes_last_topic")


def save_notes_last_topic(topic: str) -> None:
    """Save the notes window's current topic to config.json, preserving other values."""
    _save_config_value("notes_last_topic", topic)


def get_notes_last_search() -> str:
    """Get the notes window's last search text, or '' if never set."""
    return _get_config().get("notes_last_search", "")


def save_notes_last_search(text: str) -> None:
    """Save the notes window's current search text to config.json, preserving other values."""
    _save_config_value("notes_last_search", text)


def get_skip_delete_confirmation() -> bool:
    """Return True when the user opted out of the delete confirmation dialog."""
    return bool(_get_config().get("skip_delete_confirmation", False))


def save_skip_delete_confirmation(skip: bool) -> None:
    """Persist the "don't ask again" choice for delete confirmations."""
    _save_config_value("skip_delete_confirmation", skip)


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

    Tab profiles stored in the same file are preserved: when the app has
    tabs, only its app-level shortcuts are cleared and the file is kept.
    The file is removed only when no tab profiles remain.

    Args:
        app_name: The application name (e.g., 'brave-browser')

    Returns:
        True if the app profile was deleted or cleared, False if it didn't exist.
    """
    json_file = get_data_dir() / f"{app_name}.json"
    if not json_file.exists():
        return False
    data = get_app_shortcuts(app_name) or {}
    if data.get("tabs"):
        data["shortcuts"] = []
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        json_file.unlink()
    return True


def has_app_shortcuts(app_name: str) -> bool:
    """Check whether the given application has at least one recorded shortcut."""
    data = get_app_shortcuts(app_name)
    if not data:
        return False
    if data.get("shortcuts"):
        return True
    return any(t.get("shortcuts") for t in data.get("tabs", []))


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


def _get_topics_path() -> Path:
    """Return the path to the topics.json file."""
    return get_data_dir() / "topics.json"


def get_topics() -> Dict[str, List[Dict[str, str]]]:
    """
    Get all user-defined topics and their key/value entries.

    Returns:
        Dictionary mapping topic name to a list of entries.
        Format:
        {
            "git": [{"key": "compare to origin main", "value": "git diff origin/main..."}],
            ...
        }
    """
    topics_path = _get_topics_path()
    if not topics_path.exists():
        return {}
    try:
        with open(topics_path, 'r') as f:
            data = json.load(f)
            return data.get("topics", {})
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading topics: {e}")
        return {}


def save_topics(topics: Dict[str, List[Dict[str, str]]]) -> None:
    """
    Save the full topics mapping.

    Args:
        topics: Dictionary mapping topic name to a list of
                {"key": str, "value": str} entries.
    """
    topics_path = _get_topics_path()
    topics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(topics_path, 'w') as f:
        json.dump({"topics": topics}, f, indent=2)


def add_topic(name: str) -> bool:
    """Add an empty topic. Returns False if it already exists or the name is blank."""
    name = name.strip()
    if not name:
        return False
    topics = get_topics()
    if name in topics:
        return False
    topics[name] = []
    save_topics(topics)
    return True


def delete_topic(name: str) -> bool:
    """Delete a topic and all its entries. Returns False if it didn't exist."""
    topics = get_topics()
    if name not in topics:
        return False
    del topics[name]
    save_topics(topics)
    return True


def add_topic_entry(topic: str, key: str, value: str) -> bool:
    """Append a key/value entry to a topic. Returns False if the topic doesn't exist."""
    topics = get_topics()
    if topic not in topics:
        return False
    topics[topic].append({"key": key, "value": value})
    save_topics(topics)
    return True


def update_topic_entry(topic: str, index: int, key: str, value: str) -> bool:
    """Replace the entry at index in a topic. Returns False if out of range."""
    topics = get_topics()
    if topic not in topics or not (0 <= index < len(topics[topic])):
        return False
    topics[topic][index] = {"key": key, "value": value}
    save_topics(topics)
    return True


def delete_topic_entry(topic: str, index: int) -> bool:
    """Delete the entry at index in a topic. Returns False if out of range."""
    topics = get_topics()
    if topic not in topics or not (0 <= index < len(topics[topic])):
        return False
    del topics[topic][index]
    save_topics(topics)
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
