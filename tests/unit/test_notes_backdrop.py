"""Verify cached blur rendering and capture failure behavior."""
import pytest

from PyQt6.QtGui import QColor, QImage, QPixmap
from src.notes.backdrop import blurred_desktop


def test_blurs_desktop_capture_once(qapp):
    image = QImage(128, 128, QImage.Format.Format_RGB32)
    for y in range(128):
        for x in range(128):
            image.setPixelColor(x, y, QColor('white' if (x // 8 + y // 8) % 2 else 'black'))

    class Screen:
        calls = 0

        def grabWindow(self, window):
            assert window == 0
            self.calls += 1
            return QPixmap.fromImage(image)

    screen = Screen()
    result = blurred_desktop(screen).toImage()
    assert screen.calls == 1
    assert result.width() == 32
    assert 30 < result.pixelColor(16, 16).red() < 225


def test_missing_capture_has_dim_fallback(qapp):
    class Screen:
        def grabWindow(self, window):
            return QPixmap()

    assert blurred_desktop(Screen()).toImage().pixelColor(0, 0) == QColor('#151515')


@pytest.mark.parametrize("pixel_ratio", [1, 1.25, 1.5, 2])
def test_high_dpi_capture_fills_all_four_quadrants(qapp, pixel_ratio):
    from PyQt6.QtCore import QRect
    from PyQt6.QtGui import QPainter
    capture = QPixmap(512, 512)
    painter = QPainter(capture)
    colors = ['red', 'green', 'blue', 'yellow']
    for rect, color in zip((QRect(0, 0, 256, 256), QRect(256, 0, 256, 256),
                            QRect(0, 256, 256, 256), QRect(256, 256, 256, 256)), colors):
        painter.fillRect(rect, QColor(color))
    painter.end()
    capture.setDevicePixelRatio(pixel_ratio)

    class Screen:
        def grabWindow(self, window):
            return capture

    image = blurred_desktop(Screen()).toImage()
    for point, color in zip(((32, 32), (96, 32), (32, 96), (96, 96)), colors):
        actual = image.pixelColor(*point)
        expected = QColor(color)
        assert abs(actual.red() - expected.red()) < 10
        assert abs(actual.green() - expected.green()) < 10
        assert abs(actual.blue() - expected.blue()) < 10
