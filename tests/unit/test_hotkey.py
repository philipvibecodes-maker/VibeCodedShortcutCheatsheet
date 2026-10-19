"""Unit tests for the GNOME custom-keybinding helpers."""

import pytest

pytestmark = pytest.mark.skipif(
    not __import__("sys").platform.startswith("linux"), reason="GNOME-only module"
)


def test_parse_path_list():
    from src.platform.linux_gnome.hotkey import _parse_path_list

    assert _parse_path_list("@as []") == []
    assert _parse_path_list("[]") == []
    assert _parse_path_list("['/a/custom0/']") == ["/a/custom0/"]
    assert _parse_path_list("['/a/custom0/', '/a/custom1/']") == ["/a/custom0/", "/a/custom1/"]
    assert _parse_path_list("garbage") == []


def test_free_path():
    from src.platform.linux_gnome.hotkey import _PATH_PREFIX, _free_path

    assert _free_path([]) == f"{_PATH_PREFIX}custom0/"
    assert _free_path([f"{_PATH_PREFIX}custom0/"]) == f"{_PATH_PREFIX}custom1/"
    # gaps are filled from the lowest free index
    assert _free_path([f"{_PATH_PREFIX}custom1/"]) == f"{_PATH_PREFIX}custom0/"


def test_toggle_command_points_at_main(tmp_path):
    from src.platform.linux_gnome.hotkey import toggle_command

    command = toggle_command()
    assert "main.py" in command
    assert "--toggle-notes" in command
