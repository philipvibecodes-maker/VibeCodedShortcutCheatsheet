"""Verify cached blur rendering and capture failure behavior."""
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
