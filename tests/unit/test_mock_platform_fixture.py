"""Sanity checks that the shared mock_platform fixture works as advertised."""


def test_mock_returns_sample_windows(mock_platform):
    assert len(mock_platform.get_open_windows()) == 3


def test_mock_app_names(mock_platform):
    names = mock_platform.get_open_app_names()
    assert "brave-browser" in names
    assert "dev.zed.Zed" in names


def test_mock_focused_window(mock_platform):
    focused = mock_platform.get_focused_window()
    assert focused is not None
    assert focused["wm_class"] == "dev.zed.Zed"


def test_mock_focused_app_name(mock_platform):
    assert mock_platform.get_focused_app_name() == "dev.zed.Zed"


def test_mock_platform_supported(mock_platform):
    ok, _ = mock_platform.is_platform_supported()
    assert ok is True
