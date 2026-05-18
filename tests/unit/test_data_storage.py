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
