"""Low-cost focus backdrops: translucent dark, soft spotlight, or cached blur."""

from PyQt6.QtCore import QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QGraphicsBlurEffect, QGraphicsScene, QWidget


def blurred_desktop(screen):
    capture = screen.grabWindow(0)
    if capture.isNull():
        # Some compositors do not expose the desktop through XWayland.
        capture = QPixmap(1, 1)
        capture.fill(QColor("#151515"))
        return capture
    small = capture.scaled(max(1, capture.width() // 4), max(1, capture.height() // 4),
                           Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    # The scene and render image below use physical pixel coordinates. Qt
    # preserves capture DPR during scaling; at 2x that otherwise makes the
    # item occupy only the upper-left quarter of the rendering rectangle.
    small.setDevicePixelRatio(1.0)
    # Extend edge pixels before blurring. Sampling transparent space outside
    # the capture otherwise creates a dark frame around the whole desktop.
    padding = 32
    width, height = small.width(), small.height()
    padded = QPixmap(width + 2 * padding, height + 2 * padding)
    painter = QPainter(padded)
    columns = ((0, padding, 0, 1), (padding, width, 0, width),
               (padding + width, padding, width - 1, 1))
    rows = ((0, padding, 0, 1), (padding, height, 0, height),
            (padding + height, padding, height - 1, 1))
    for x, w, sx, sw in columns:
        for y, h, sy, sh in rows:
            painter.drawPixmap(QRect(x, y, w, h), small, QRect(sx, sy, sw, sh))
    painter.end()
    scene = QGraphicsScene()
    item = scene.addPixmap(padded)
    blur = QGraphicsBlurEffect()
    blur.setBlurRadius(10)
    item.setGraphicsEffect(blur)
    source = QRectF(padding, padding, width, height)
    target = QRectF(0, 0, width, height)
    image = QImage(small.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#151515"))
    painter = QPainter(image)
    scene.render(painter, target, source)
    painter.end()
    return QPixmap.fromImage(image)


class NotesBackdrop(QWidget):
    def __init__(self, screen, close_notes, style="dim"):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.X11BypassWindowManagerHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(screen.geometry())
        self.style = style
        self._image = None
        if style == "blur":
            self._image = blurred_desktop(screen).scaled(
                screen.geometry().size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        self._spotlight = QRadialGradient(
            self.rect().center().toPointF(), max(self.width(), self.height()) * 0.65)
        self._spotlight.setColorAt(0.0, QColor(9, 12, 18, 120))
        self._spotlight.setColorAt(0.6, QColor(9, 12, 18, 205))
        self._spotlight.setColorAt(1.0, QColor(9, 12, 18, 255))
        self._tint = QColor(9, 12, 18)
        if style == "spotlight":
            self._image = QPixmap(self.size())
            self._image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(self._image)
            painter.fillRect(self.rect(), self._spotlight)
            painter.end()
        self.strength = 0.0
        self._close_notes = close_notes

    def setStrength(self, strength):
        strength = max(0.0, min(1.0, strength))
        if self.strength != strength:
            self.strength = strength
            self.update()

    def paintEvent(self, event):
        # Composite the cached image directly. A graphics opacity effect on a
        # screen-sized widget adds an unnecessary full-screen intermediate.
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setOpacity(self.strength)
        if self._image is not None:
            painter.drawPixmap(0, 0, self._image)
        else:
            painter.fillRect(event.rect(), self._tint)
        painter.end()

    def mousePressEvent(self, event):
        self._close_notes()
        event.accept()
