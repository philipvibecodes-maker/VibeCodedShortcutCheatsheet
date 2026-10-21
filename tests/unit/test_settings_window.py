"""Unit tests for helpers in settings_window."""

from src.settings.settings_window import _is_browser_app, site_name_from_title


def test_is_browser_app():
    for name in ("chrome.exe", "firefox", "brave-browser", "msedge.exe",
                 "chromium", "opera", "vivaldi"):
        assert _is_browser_app(name), name


def test_is_browser_app_rejects_non_browsers():
    for name in ("gnome-terminal-server", "WindowsTerminal.exe", "Code.exe",
                 "notepad.exe", ""):
        assert not _is_browser_app(name), name


def test_site_name_prefers_url_domain():
    assert site_name_from_title(
        "https://github.com/user/repo - Google Chrome") == "github.com"
    assert site_name_from_title(
        "www.gmail.com/mail - Google Chrome") == "gmail.com"


def test_site_name_strips_www_prefix():
    assert site_name_from_title(
        "https://www.reddit.com/r/python - Chrome") == "reddit.com"


def test_site_name_bare_domain_in_title():
    assert site_name_from_title("docs.astral.sh - Google Chrome") == "docs.astral.sh"
    assert site_name_from_title(
        "uv | docs.astral.sh - Google Chrome") == "docs.astral.sh"


def test_site_name_ignores_filenames():
    # "settings.py" looks like a domain but .py isn't a site TLD
    assert site_name_from_title("settings.py - Google Chrome") == "settings.py"


def test_site_name_last_segment_minus_browser():
    assert site_name_from_title(
        "user/repo: Description - GitHub - Google Chrome") == "GitHub"
    assert site_name_from_title("Inbox - Gmail - Google Chrome") == "Gmail"
    assert site_name_from_title("Some Page — Mozilla Firefox") == "Some Page"


def test_site_name_no_separator_returns_title():
    assert site_name_from_title("GitHub") == "GitHub"
    assert site_name_from_title("") == ""
