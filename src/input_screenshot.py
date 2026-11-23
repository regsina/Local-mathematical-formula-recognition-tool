from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget


class ScreenshotOverlay(QWidget):
    grabbed = Signal(QPixmap)
    cancelled = Signal()

    def __init__(self, pixmap: QPixmap):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._pixmap = pixmap
        self._origin = None
        self._current = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setGeometry(
            self._pixmap.geometry()
            if hasattr(self._pixmap, "geometry")
            else self.geometry()
        )
        self.showFullScreen()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            self._current = event.position().toPoint()
            rect = self._selection_rect()
            if rect.width() >= 4 and rect.height() >= 4:
                dpr = self._pixmap.devicePixelRatio()
                scaled = self._pixmap.rect()
                from PySide6.QtCore import QRect

                grab_rect = QRect(
                    int(rect.x() * dpr),
                    int(rect.y() * dpr),
                    int(rect.width() * dpr),
                    int(rect.height() * dpr),
                )
                grab_rect = grab_rect.intersected(scaled)
                if not grab_rect.isEmpty():
                    result = self._pixmap.copy(grab_rect)
                    result.setDevicePixelRatio(1.0)
                    self.grabbed.emit(result)
                    self.close()
                    return
            self._origin = None
            self._current = None
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def _selection_rect(self):
        from PySide6.QtCore import QRect

        if self._origin is None or self._current is None:
            return QRect()
        return QRect(self._origin, self._current).normalized()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        rect = self._selection_rect()
        if not rect.isEmpty():
            painter.drawPixmap(rect, self._pixmap, rect)
            painter.setPen(QPen(QColor(0, 150, 255), 2))
            painter.drawRect(rect)
        painter.end()


def grab_interactive(screen) -> ScreenshotOverlay:
    pixmap = screen.grabWindow(0)
    overlay = ScreenshotOverlay(pixmap)
    return overlay
