"""Unit tests for data_storage — isolated from the real data/ directory."""

import json

import pytest

from src import data_storage


@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    """Redirect data_storage to a temp dir populated with sample JSON files."""
    monkeypatch.setattr(data_storage, "get_data_dir", lambda: tmp_path)

    (tmp_path / "brave-browser.json").write_text(json.dumps({
        "app_name": "brave-browser",
        "display_name": "Brave Browser",
        "shortcuts": [{"keys": "Ctrl+T", "description": "New tab"}],
    }))
    (tmp_path / "default.json").write_text(json.dumps({
        "app_name": "default",
        "display_name": "Ubuntu (Default)",
        "shortcuts": [{"keys": "Super", "description": "Overview"}],
    }))
    return tmp_path


def test_get_app_shortcuts_existing(temp_data_dir):
    result = data_storage.get_app_shortcuts("brave-browser")
    assert result is not None
    assert result["display_name"] == "Brave Browser"
    assert result["shortcuts"][0]["keys"] == "Ctrl+T"


def test_get_app_shortcuts_missing(temp_data_dir):
    assert data_storage.get_app_shortcuts("does-not-exist") is None


def test_get_all_app_names(temp_data_dir):
    names = set(data_storage.get_all_app_names())
    assert names == {"brave-browser", "default"}


def test_get_default_shortcuts(temp_data_dir):
    defaults = data_storage.get_default_shortcuts()
    assert defaults is not None
    assert defaults["app_name"] == "default"


def test_has_app_shortcuts(temp_data_dir):
    assert data_storage.has_app_shortcuts("brave-browser") is True
    assert data_storage.has_app_shortcuts("ghost") is False


def test_save_and_delete_app_shortcuts(temp_data_dir):
    data_storage.save_app_shortcuts("newapp", [{"keys": "F1", "description": "Help"}])
    assert data_storage.has_app_shortcuts("newapp")

    loaded = data_storage.get_app_shortcuts("newapp")
    assert loaded["shortcuts"][0]["keys"] == "F1"
    # display_name defaults to app_name on first save
    assert loaded["display_name"] == "newapp"

    assert data_storage.delete_app_shortcuts("newapp") is True
    assert data_storage.delete_app_shortcuts("newapp") is False


def test_font_size_default_and_roundtrip(temp_data_dir):
    assert data_storage.get_font_size() == 12
    data_storage.save_font_size(18)
    assert data_storage.get_font_size() == 18


def test_tab_profiles_empty(temp_data_dir):
    assert data_storage.get_tab_profiles("brave-browser") == []
    assert data_storage.get_tab_profiles("does-not-exist") == []


def test_save_and_get_tab_shortcuts(temp_data_dir):
    data_storage.save_tab_shortcuts(
        "brave-browser", "GitHub",
        [{"keys": "?", "description": "Show shortcuts"}],
    )
    tab = data_storage.get_tab_shortcuts(
        "brave-browser", "philipvibecodes-maker/MathCompile: GitHub - Brave"
    )
    assert tab is not None
    assert tab["pattern"] == "GitHub"
    assert tab["shortcuts"][0]["keys"] == "?"


def test_tab_match_is_case_insensitive_substring(temp_data_dir):
    data_storage.save_tab_shortcuts("brave-browser", "gmail", [])
    assert data_storage.get_tab_shortcuts("brave-browser", "Inbox - GMAIL - Brave") is not None
    assert data_storage.get_tab_shortcuts("brave-browser", "Other site - Brave") is None


def test_tab_match_longest_pattern_wins(temp_data_dir):
    data_storage.save_tab_shortcuts("brave-browser", "GitHub",
        [{"keys": "?", "description": "generic"}])
    data_storage.save_tab_shortcuts("brave-browser", "GitHub Issues",
        [{"keys": "c", "description": "specific"}])
    tab = data_storage.get_tab_shortcuts("brave-browser", "GitHub Issues - Brave")
    assert tab["shortcuts"][0]["description"] == "specific"


def test_tab_shortcuts_empty_title(temp_data_dir):
    data_storage.save_tab_shortcuts("brave-browser", "GitHub", [])
    assert data_storage.get_tab_shortcuts("brave-browser", "") is None
    assert data_storage.get_tab_shortcuts("brave-browser", None) is None


def test_save_tab_shortcuts_updates_existing(temp_data_dir):
    data_storage.save_tab_shortcuts("brave-browser", "GitHub", [{"keys": "a", "description": "x"}])
    data_storage.save_tab_shortcuts("brave-browser", "GitHub", [{"keys": "b", "description": "y"}])
    tabs = data_storage.get_tab_profiles("brave-browser")
    assert len(tabs) == 1
    assert tabs[0]["shortcuts"][0]["keys"] == "b"


def test_save_tab_shortcuts_preserves_app_shortcuts(temp_data_dir):
    data_storage.save_tab_shortcuts("brave-browser", "GitHub", [])
    data = data_storage.get_app_shortcuts("brave-browser")
    assert data["shortcuts"][0]["keys"] == "Ctrl+T"
    assert data["tabs"][0]["pattern"] == "GitHub"


def test_save_tab_shortcuts_creates_app_file(temp_data_dir):
    data_storage.save_tab_shortcuts("newapp", "sometab",
        [{"keys": "x", "description": "y"}])
    assert data_storage.has_app_shortcuts("newapp")
    assert data_storage.get_tab_shortcuts("newapp", "sometab - Browser") is not None


def test_delete_tab_shortcuts(temp_data_dir):
    data_storage.save_tab_shortcuts("brave-browser", "GitHub", [])
    assert data_storage.delete_tab_shortcuts("brave-browser", "GitHub") is True
    assert data_storage.delete_tab_shortcuts("brave-browser", "GitHub") is False
    assert data_storage.get_tab_profiles("brave-browser") == []


def test_delete_app_shortcuts_preserves_tabs(temp_data_dir):
    data_storage.save_tab_shortcuts(
        "brave-browser", "GitHub", [{"keys": "g", "description": "tab"}])

    assert data_storage.delete_app_shortcuts("brave-browser") is True

    data = data_storage.get_app_shortcuts("brave-browser")
    assert data is not None
    assert data["shortcuts"] == []
    assert data["tabs"][0]["pattern"] == "GitHub"
    assert data["tabs"][0]["shortcuts"][0]["keys"] == "g"


def test_delete_app_shortcuts_removes_file_without_tabs(temp_data_dir):
    assert data_storage.delete_app_shortcuts("brave-browser") is True
    assert data_storage.get_app_shortcuts("brave-browser") is None


def test_notes_last_topic_roundtrip(temp_data_dir):
    assert data_storage.get_notes_last_topic() is None
    data_storage.save_notes_last_topic("git")
    assert data_storage.get_notes_last_topic() == "git"
    # independent of other notes config
    data_storage.save_notes_font_size(20)
    assert data_storage.get_notes_last_topic() == "git"


def test_notes_font_size_independent(temp_data_dir):
    assert data_storage.get_notes_font_size() == 12
    data_storage.save_notes_font_size(20)
    assert data_storage.get_notes_font_size() == 20
    # independent of the cheatsheet font size
    assert data_storage.get_font_size() == 12
    data_storage.save_font_size(9)
    assert data_storage.get_notes_font_size() == 20
