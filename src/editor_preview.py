from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import config
from .renderer import render_latex


class SourceEditor(QPlainTextEdit):
    editingSettled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(config.AUTOSAVE_DEBOUNCE_MS)
        self._timer.timeout.connect(self._emit_settled)
        self.textChanged.connect(self._on_changed)

    def _on_changed(self) -> None:
        self._timer.start()

    def _emit_settled(self) -> None:
        self.editingSettled.emit(self.toPlainText())

    def flush(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self._emit_settled()


class PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._image_label = QLabel("暂无预览")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumHeight(160)
        self._image_label.setStyleSheet("background: white; border: 1px solid #ccc;")
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #b00020;")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._image_label, 1)
        layout.addWidget(self._error_label)
        self._render_failed = False

    @property
    def render_failed(self) -> bool:
        return self._render_failed

    def render_source(self, latex: str) -> None:
        result = render_latex(latex)
        if result.ok:
            self._render_failed = False
            pm = QPixmap.fromImage(result.image)
            self._image_label.setPixmap(
                pm.scaled(
                    self._image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._error_label.hide()
        else:
            self._render_failed = True
            self._error_label.setText(
                f"{result.error}（渲染失败状态将保持显示，可继续编辑或撤销）"
            )
            self._error_label.show()

    def clear(self, message: str = "暂无预览") -> None:
        self._render_failed = False
        self._image_label.setText(message)
        self._error_label.hide()


class EditorPreview(QWidget):
    previewRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor = SourceEditor()
        self.editor.setPlaceholderText("识别结果源码，可编辑")
        self.preview = PreviewPanel()
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.editor.editingSettled.connect(self.previewRequested)
