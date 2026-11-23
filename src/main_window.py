import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QGuiApplication, QImage, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import config
from .editor_preview import EditorPreview
from .history_panel import HistoryPanel
from .history_store import HistoryRecord, HistoryStore
from .input_canvas import CanvasWidget
from .input_screenshot import grab_interactive
from .recognizer.factory import create_default_recognizer
from .task_manager import STATE_CANCELLING, TaskManager

INPUT_SCREENSHOT = "截图"
INPUT_IMPORT = "图片导入"
INPUT_CANVAS = "鼠标手写"

MULTI_FORMULA_HINT = (
    "如框选区域包含多个相互独立的公式，结果可能不符合预期，建议重新框选单个公式区域。"
)


class MainWindow(QMainWindow):
    def __init__(self, store: HistoryStore | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(config.APP_DISPLAY_NAME)
        self.resize(1100, 720)
        self._store = store or HistoryStore()
        self._recognizer = create_default_recognizer()
        self._task_manager = TaskManager(self._recognizer, self)
        self._current_image: QImage | None = None
        self._current_method: str = ""
        self._current_original_path: str | None = None
        self._current_record: HistoryRecord | None = None
        self._dirty = False
        self._overlay = None
        self._build_ui()
        self._wire_task_manager()
        self._update_action_state()

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_screenshot_tab(), "截图识别")
        self._tabs.addTab(self._build_import_tab(), "图片导入")
        self._tabs.addTab(self._build_canvas_tab(), "鼠标手写")
        self._history_panel = HistoryPanel(self._store)
        self._tabs.addTab(self._history_panel, "历史记录")
        splitter.addWidget(self._tabs)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self._result_image_label = QLabel("暂无输入图像")
        self._result_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_image_label.setMinimumHeight(140)
        self._result_image_label.setStyleSheet(
            "background: #fafafa; border: 1px solid #ddd;"
        )
        self._hint_label = QLabel(MULTI_FORMULA_HINT)
        self._hint_label.setStyleSheet("color: #8a6d00;")
        self._hint_label.setWordWrap(True)
        self._raw_label = QLabel("原始识别源码：-")
        self._raw_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._raw_label.setWordWrap(True)
        self._editor_preview = EditorPreview()
        btn_row = QHBoxLayout()
        self._copy_btn = QPushButton("复制当前源码")
        self._cancel_btn = QPushButton("取消识别")
        self._new_btn = QPushButton("开始新输入")
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._new_btn)
        self._status_label = QLabel("就绪")
        self._unsaved_label = QLabel("")
        self._unsaved_label.setStyleSheet("color: #b00020;")
        right_layout.addWidget(self._result_image_label)
        right_layout.addWidget(self._hint_label)
        right_layout.addWidget(self._raw_label)
        right_layout.addWidget(self._editor_preview, 1)
        right_layout.addLayout(btn_row)
        right_layout.addWidget(self._status_label)
        right_layout.addWidget(self._unsaved_label)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        self._copy_btn.clicked.connect(self._copy_source)
        self._cancel_btn.clicked.connect(self._task_manager.cancel)
        self._new_btn.clicked.connect(self._start_new_input)
        self._editor_preview.editor.textChanged.connect(self._on_source_changed)
        self._editor_preview.editor.editingSettled.connect(self._on_source_settled)
        self._editor_preview.previewRequested.connect(self._render_preview)
        self._history_panel.recordOpenRequested.connect(self._open_record)
        self._history_panel.recordDeleted.connect(self._on_record_deleted)

    def _build_screenshot_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._shot_btn = QPushButton("开始截图框选（Esc 取消）")
        self._shot_preview = QLabel("尚未截图")
        self._shot_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._shot_preview.setMinimumHeight(200)
        self._shot_preview.setStyleSheet("background: #fafafa; border: 1px solid #ddd;")
        self._shot_submit = QPushButton("提交识别")
        self._shot_btn.clicked.connect(self._start_screenshot)
        self._shot_submit.clicked.connect(lambda: self._submit(INPUT_SCREENSHOT))
        layout.addWidget(self._shot_btn)
        layout.addWidget(self._shot_preview, 1)
        layout.addWidget(self._shot_submit)
        return w

    def _build_import_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._import_btn = QPushButton("选择图片（PNG/JPG/JPEG）")
        self._import_preview = QLabel("尚未选择图片")
        self._import_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._import_preview.setMinimumHeight(200)
        self._import_preview.setStyleSheet(
            "background: #fafafa; border: 1px solid #ddd;"
        )
        self._import_submit = QPushButton("提交识别")
        self._import_btn.clicked.connect(self._choose_image)
        self._import_submit.clicked.connect(lambda: self._submit(INPUT_IMPORT))
        layout.addWidget(self._import_btn)
        layout.addWidget(self._import_preview, 1)
        layout.addWidget(self._import_submit)
        return w

    def _build_canvas_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._canvas = CanvasWidget()
        row = QHBoxLayout()
        self._pen_btn = QPushButton("画笔")
        self._eraser_btn = QPushButton("橡皮擦")
        self._undo_btn = QPushButton("撤销")
        self._clear_btn = QPushButton("清空")
        self._canvas_submit = QPushButton("提交识别")
        for b in (
            self._pen_btn,
            self._eraser_btn,
            self._undo_btn,
            self._clear_btn,
            self._canvas_submit,
        ):
            row.addWidget(b)
        self._pen_btn.clicked.connect(lambda: self._canvas.set_eraser(False))
        self._eraser_btn.clicked.connect(lambda: self._canvas.set_eraser(True))
        self._undo_btn.clicked.connect(self._canvas.undo)
        self._clear_btn.clicked.connect(self._canvas.clear)
        self._canvas_submit.clicked.connect(lambda: self._submit(INPUT_CANVAS))
        layout.addWidget(self._canvas, 1)
        layout.addLayout(row)
        return w

    def _wire_task_manager(self) -> None:
        self._task_manager.stateChanged.connect(self._on_task_state)
        self._task_manager.recognizeSucceeded.connect(self._on_recognize_succeeded)
        self._task_manager.recognizeFailed.connect(self._on_recognize_failed)
        self._task_manager.cancelFinished.connect(self._on_cancel_finished)

    def _start_screenshot(self) -> None:
        if self._task_manager.is_busy():
            return
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            QMessageBox.warning(self, "截图失败", "未检测到可用屏幕。")
            return
        self.showMinimized()
        self._overlay = grab_interactive(screen)
        self._overlay.grabbed.connect(self._on_screenshot_grabbed)
        self._overlay.cancelled.connect(self._on_screenshot_cancelled)
        self._overlay.destroyed.connect(self.showNormal)

    def _on_screenshot_grabbed(self, pixmap: QPixmap) -> None:
        image = pixmap.toImage()
        self.showNormal()
        self._set_input_image(image, INPUT_SCREENSHOT, None, self._shot_preview)

    def _on_screenshot_cancelled(self) -> None:
        self.showNormal()
        self._status_label.setText("截图已取消，未启动识别")

    def _choose_image(self) -> None:
        if self._task_manager.is_busy():
            return
        path, _flt = QFileDialog.getOpenFileName(
            self, "选择公式图片", "", "图片文件 (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            if os.path.getsize(path) > config.MAX_FILE_BYTES:
                if not self._confirm_oversize("文件大小超过限制"):
                    return
            reader = QImageReader(path)
            reader.setAutoTransform(True)
            image = reader.read()
            if image.isNull():
                QMessageBox.warning(
                    self,
                    "无法解码",
                    f"图片无法解码：{reader.errorString()}。请重新选择或截图。",
                )
                return
        except OSError as exc:
            QMessageBox.warning(self, "读取失败", f"无法读取文件：{exc}")
            return
        if image.width() * image.height() > config.MAX_IMAGE_PIXELS:
            if not self._confirm_oversize(
                f"像素数 {image.width()}x{image.height()} 超过限制"
            ):
                return
            image = image.scaled(
                4096,
                4096,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._status_label.setText("输入已按策略缩放，可能影响识别质量（已记录）")
        self._set_input_image(image, INPUT_IMPORT, path, self._import_preview)

    def _confirm_oversize(self, reason: str) -> bool:
        answer = QMessageBox.question(
            self,
            "输入超限",
            f"{reason}（上限为拟定值，G1 冻结）。\n默认拒绝：选择“否”返回重新选择；选择“是”按策略缩放后继续，可能影响识别质量。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _set_input_image(
        self,
        image: QImage,
        method: str,
        original_path: str | None,
        preview_label: QLabel,
    ) -> None:
        self._current_image = image
        self._current_method = method
        self._current_original_path = original_path
        self._current_record = None
        self._dirty = False
        self._unsaved_label.setText("")
        pm = QPixmap.fromImage(image)
        for label in (preview_label, self._result_image_label):
            label.setPixmap(
                pm.scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self._status_label.setText(f"已载入{method}输入，可提交识别")

    def _submit(self, method: str) -> None:
        if self._task_manager.is_busy():
            return
        image = self._current_image
        if method == INPUT_CANVAS:
            if self._canvas.is_blank():
                self._status_label.setText("画板为空，请书写后再提交")
                return
            image = self._canvas.export_image()
            self._current_image = image
            self._current_method = method
            self._current_original_path = None
            self._result_image_label.setPixmap(
                QPixmap.fromImage(image).scaled(
                    self._result_image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        if image is None or self._current_method != method:
            self._status_label.setText("请先提供有效输入")
            return
        self._status_label.setText("识别中…")
        self._update_action_state()
        self._task_manager.start(image)

    def _on_task_state(self, state: str) -> None:
        if state == STATE_CANCELLING:
            self._status_label.setText("取消中，等待任务退出…")
        self._update_action_state()

    def _on_recognize_succeeded(
        self, _task_id: int, latex: str, model_name: str, model_version: str
    ) -> None:
        self._editor_preview.editor.blockSignals(True)
        self._editor_preview.editor.setPlainText(latex)
        self._editor_preview.editor.blockSignals(False)
        self._raw_label.setText(
            f"原始识别源码（{model_name} {model_version}）：{latex}"
        )
        self._render_preview(latex)
        try:
            rec = self._store.create_record(
                input_method=self._current_method,
                image=self._current_image,
                raw_latex=latex,
                model_name=model_name,
                model_version=model_version,
                original_path=self._current_original_path,
            )
            self._current_record = rec
            self._dirty = False
            self._unsaved_label.setText("")
            self._history_panel.reload()
            self._status_label.setText("识别成功，已建立历史记录")
        except OSError as exc:
            self._current_record = None
            self._dirty = True
            self._unsaved_label.setText(
                f"历史保存失败（未保存）：{exc}。识别与编辑不受影响，可重试保存。"
            )
            self._status_label.setText("识别成功，但历史保存失败")

    def _on_recognize_failed(self, _task_id: int, reason: str) -> None:
        self._status_label.setText(f"识别失败：{reason}。输入已保留，可修改后重试。")
        self._update_action_state()

    def _on_cancel_finished(self) -> None:
        self._status_label.setText("已取消，返回可编辑输入状态")
        self._update_action_state()

    def _on_source_changed(self) -> None:
        if (
            self._current_record is not None
            or self._editor_preview.editor.toPlainText().strip()
        ):
            self._dirty = True

    def _on_source_settled(self, text: str) -> None:
        self._render_preview(text)
        self._autosave(text)

    def _render_preview(self, text: str) -> None:
        if text.strip():
            self._editor_preview.preview.render_source(text)
        else:
            self._editor_preview.preview.clear()

    def _autosave(self, text: str) -> None:
        if self._current_record is None:
            return
        if self._store.update_source(self._current_record, text):
            self._dirty = False
            self._unsaved_label.setText("")
            self._status_label.setText("已自动保存")
        else:
            self._dirty = True
            self._unsaved_label.setText("保存失败（未保存），可继续编辑触发重试")

    def _copy_source(self) -> None:
        text = self._editor_preview.editor.toPlainText()
        if not text.strip():
            self._status_label.setText("源码为空，无法复制")
            return
        if self._editor_preview.preview.render_failed:
            QMessageBox.information(
                self, "渲染未通过", "当前源码未通过预览，仍将按原文复制。"
            )
        try:
            QGuiApplication.clipboard().setText(text)
            self._status_label.setText("已复制到剪贴板（Unicode 纯文本）")
        except Exception as exc:
            QMessageBox.warning(
                self,
                "剪贴板写入失败",
                f"复制失败：{exc}。可直接在编辑器中全选手动复制（Ctrl+A / Ctrl+C）。",
            )

    def _open_record(self, rec: HistoryRecord) -> None:
        if self._task_manager.is_busy():
            return
        if rec.image_path:
            image = QImage(rec.image_path)
            if not image.isNull():
                self._current_image = image
                self._result_image_label.setPixmap(
                    QPixmap.fromImage(image).scaled(
                        self._result_image_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        self._current_record = rec
        self._current_method = rec.input_method
        self._current_original_path = None
        self._editor_preview.editor.blockSignals(True)
        self._editor_preview.editor.setPlainText(rec.edited_latex)
        self._editor_preview.editor.blockSignals(False)
        self._raw_label.setText(
            f"原始识别源码（{rec.model_name} {rec.model_version}）：{rec.raw_latex}"
        )
        self._render_preview(rec.edited_latex)
        self._dirty = False
        self._unsaved_label.setText("")
        self._status_label.setText(
            f"已打开历史记录（{rec.updated_at}），继续编辑将自动保存"
        )

    def _on_record_deleted(self) -> None:
        self._status_label.setText("记录已删除")

    def _start_new_input(self) -> None:
        if self._task_manager.is_busy():
            return
        self._editor_preview.editor.flush()
        self._current_image = None
        self._current_record = None
        self._current_original_path = None
        self._dirty = False
        self._unsaved_label.setText("")
        self._editor_preview.editor.clear()
        self._editor_preview.preview.clear()
        self._raw_label.setText("原始识别源码：-")
        self._result_image_label.setText("暂无输入图像")
        self._status_label.setText("已开始新输入")

    def _update_action_state(self) -> None:
        busy = self._task_manager.is_busy()
        cancelling = self._task_manager.state == STATE_CANCELLING
        for btn in (
            self._shot_submit,
            self._import_submit,
            self._canvas_submit,
            self._shot_btn,
            self._import_btn,
            self._new_btn,
        ):
            btn.setEnabled(not busy)
        self._cancel_btn.setEnabled(busy and not cancelling)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._task_manager.is_busy():
            answer = QMessageBox.question(
                self,
                "识别进行中",
                "识别仍在进行。取消并退出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._task_manager.cancel()
        self._editor_preview.editor.flush()
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "存在未保存修改",
                "存在未保存的修改。\n“是”：返回编辑并重试保存；“否”：仍要退出（可能丢失本次未保存内容）。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._autosave(self._editor_preview.editor.toPlainText())
                event.ignore()
                return
        event.accept()
