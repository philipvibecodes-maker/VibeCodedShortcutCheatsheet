"""A cached desktop blur; only its compositing strength changes per frame."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsBlurEffect, QGraphicsOpacityEffect, QGraphicsScene, QLabel


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
    scene = QGraphicsScene()
    item = scene.addPixmap(small)
    blur = QGraphicsBlurEffect()
    blur.setBlurRadius(10)
    item.setGraphicsEffect(blur)
    rect = QRectF(0, 0, small.width(), small.height())
    image = QImage(small.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#151515"))
    painter = QPainter(image)
    scene.render(painter, rect, rect)
    painter.end()
    return QPixmap.fromImage(image)


class NotesBackdrop(QLabel):
    def __init__(self, screen, close_notes):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.X11BypassWindowManagerHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setGeometry(screen.geometry())
        self.setPixmap(blurred_desktop(screen))
        self.setScaledContents(True)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0)
        self.setGraphicsEffect(self._effect)
        self._close_notes = close_notes

    def setStrength(self, strength):
        self._effect.setOpacity(strength)

    def mousePressEvent(self, event):
        self._close_notes()
        event.accept()
