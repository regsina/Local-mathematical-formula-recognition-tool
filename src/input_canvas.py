from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from . import config


class CanvasWidget(QWidget):
    strokesChanged = Signal()

    PEN_COLOR = QColor(20, 20, 20)
    BACKGROUND_COLOR = QColor(255, 255, 255)
    PEN_WIDTH = 4
    ERASER_WIDTH = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self._strokes: list[dict] = []
        self._current: dict | None = None
        self._eraser_mode = False
        self.setMouseTracking(False)

    def set_eraser(self, on: bool) -> None:
        self._eraser_mode = on

    def is_blank(self) -> bool:
        return not any(s["points"] for s in self._strokes)

    def undo(self) -> None:
        if self._current is not None:
            self._current = None
        if self._strokes:
            self._strokes.pop()
            self.update()
            self.strokesChanged.emit()

    def clear(self) -> None:
        self._strokes = []
        self._current = None
        self.update()
        self.strokesChanged.emit()

    def export_image(self) -> QImage:
        image = QImage(
            config.CANVAS_EXPORT_WIDTH,
            config.CANVAS_EXPORT_HEIGHT,
            QImage.Format.Format_RGB888,
        )
        image.fill(self.BACKGROUND_COLOR)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        sx = config.CANVAS_EXPORT_WIDTH / max(self.width(), 1)
        sy = config.CANVAS_EXPORT_HEIGHT / max(self.height(), 1)
        self._draw_strokes(painter, sx, sy)
        painter.end()
        return image

    def _draw_strokes(
        self, painter: QPainter, sx: float = 1.0, sy: float = 1.0
    ) -> None:
        strokes = list(self._strokes)
        if self._current is not None:
            strokes.append(self._current)
        for stroke in strokes:
            color = self.BACKGROUND_COLOR if stroke["eraser"] else self.PEN_COLOR
            width = self.ERASER_WIDTH if stroke["eraser"] else self.PEN_WIDTH
            pen = QPen(
                color,
                width * (sx + sy) / 2,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            points = stroke["points"]
            for i in range(1, len(points)):
                painter.drawLine(
                    QPointF(points[i - 1].x() * sx, points[i - 1].y() * sy),
                    QPointF(points[i].x() * sx, points[i].y() * sy),
                )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.BACKGROUND_COLOR)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_strokes(painter)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._current = {"eraser": self._eraser_mode, "points": [event.position()]}
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._current is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._current["points"].append(event.position())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._current is not None:
            self._current["points"].append(event.position())
            self._strokes.append(self._current)
            self._current = None
            self.update()
            self.strokesChanged.emit()
