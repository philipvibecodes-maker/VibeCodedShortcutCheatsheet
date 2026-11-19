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
    backdrop = NotesBackdrop(screen, lambda: None, "blur")
    backdrop.prepareAfterFocus(QRect(20, 20, 40, 40))
    qtbot.addWidget(backdrop)
    for strength in (0.0, 0.5, 1.0):
        backdrop.setStrength(strength)
        pixel = backdrop.grab().toImage().pixelColor(64, 64)
        assert abs(pixel.alpha() - round(255 * strength)) <= 1
    assert screen.calls == 2
    assert backdrop.graphicsEffect() is None


@pytest.mark.parametrize('style', ['dim', 'spotlight'])
def test_dark_backgrounds_need_no_capture_and_have_correct_opacity(qtbot, style):
    from PyQt6.QtCore import QRect
    from src.notes.backdrop import NotesBackdrop

    class Screen:
        def geometry(self):
            return QRect(0, 0, 200, 200)

        def grabWindow(self, window):
            pytest.fail('Dark background styles must not capture the desktop')

    backdrop = NotesBackdrop(Screen(), lambda: None, style)
    qtbot.addWidget(backdrop)
    backdrop.setStrength(0.6)
    image = backdrop.grab().toImage()
    center = image.pixelColor(100, 100)
    edge = image.pixelColor(0, 0)
    assert center.red() < 15 and center.blue() < 25
    if style == 'dim':
        assert center == edge
        assert abs(center.alpha() - 153) <= 1
    else:
        assert 60 < center.alpha() < edge.alpha() <= 153
    backdrop.setStrength(0)
    assert backdrop.grab().toImage().pixelColor(0, 0).alpha() == 0


def test_blur_refreshes_focus_colors_without_capturing_notes(qtbot):
    from PyQt6.QtCore import QRect
    from PyQt6.QtGui import QPainter
    from src.notes.backdrop import NotesBackdrop
    active = QColor('#335d8e')
    inactive = QColor('#233340')

    class Screen:
        calls = 0

        def geometry(self):
            return QRect(0, 0, 400, 400)

        def grabWindow(self, window):
            self.calls += 1
            image = QPixmap(800, 800)
            image.fill(active if self.calls == 1 else inactive)
            if self.calls == 2:
                painter = QPainter(image)
                painter.fillRect(QRect(200, 200, 200, 200), QColor('red'))
                painter.end()
            image.setDevicePixelRatio(2)
            return image

    screen = Screen()
    backdrop = NotesBackdrop(screen, lambda: None, 'blur')
    qtbot.addWidget(backdrop)
    assert screen.calls == 1
    backdrop.prepareAfterFocus(QRect(100, 100, 100, 100))
    result = backdrop._image.toImage()
    outside = result.pixelColor(20, 20)
    protected = result.pixelColor(150, 150)
    assert abs(outside.blue() - inactive.blue()) <= 3
    assert abs(protected.blue() - active.blue()) <= 3
    assert protected.red() < 70  # The foreground's red pixels were scrubbed.
    assert backdrop._clean_capture is None
    backdrop.prepareAfterFocus(QRect(100, 100, 100, 100))
    assert screen.calls == 2
