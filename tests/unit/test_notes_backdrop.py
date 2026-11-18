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


def test_blur_does_not_darken_screen_edges(qapp):
    class Screen:
        def grabWindow(self, window):
            image = QPixmap(256, 256)
            image.fill(QColor('#80a0c0'))
            return image

    image = blurred_desktop(Screen()).toImage()
    for x, y in ((0, 0), (63, 0), (0, 63), (63, 63), (32, 32)):
        color = image.pixelColor(x, y)
        assert abs(color.red() - 128) <= 3
        assert abs(color.green() - 160) <= 3
        assert abs(color.blue() - 192) <= 3
        assert color.alpha() == 255


def test_backdrop_paints_cached_image_with_requested_alpha(qtbot):
    from PyQt6.QtCore import QRect
    from src.notes.backdrop import NotesBackdrop

    class Screen:
        calls = 0

        def geometry(self):
            return QRect(0, 0, 128, 128)

        def grabWindow(self, window):
            self.calls += 1
            image = QPixmap(128, 128)
            image.fill(QColor('white'))
            return image

    screen = Screen()
    backdrop = NotesBackdrop(screen, lambda: None)
    qtbot.addWidget(backdrop)
    for strength in (0.0, 0.5, 1.0):
        backdrop.setStrength(strength)
        pixel = backdrop.grab().toImage().pixelColor(64, 64)
        assert abs(pixel.alpha() - round(255 * strength)) <= 1
    assert screen.calls == 1
    assert backdrop.graphicsEffect() is None
