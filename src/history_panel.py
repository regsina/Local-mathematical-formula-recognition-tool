from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .history_store import (
    STATUS_READ_ERROR,
    STATUS_SAVE_FAILED,
    HistoryRecord,
    HistoryStore,
)


class HistoryPanel(QWidget):
    recordOpenRequested = Signal(object)
    recordDeleted = Signal()

    def __init__(self, store: HistoryStore, parent=None):
        super().__init__(parent)
        self._store = store
        layout = QVBoxLayout(self)
        self._info_label = QLabel("")
        self._list = QListWidget()
        btn_row = QHBoxLayout()
        self._open_btn = QPushButton("打开")
        self._delete_btn = QPushButton("删除")
        self._refresh_btn = QPushButton("刷新")
        btn_row.addWidget(self._open_btn)
        btn_row.addWidget(self._delete_btn)
        btn_row.addWidget(self._refresh_btn)
        layout.addWidget(self._info_label)
        layout.addWidget(self._list, 1)
        layout.addLayout(btn_row)
        self._records: list[HistoryRecord] = []
        self._open_btn.clicked.connect(self._open_current)
        self._delete_btn.clicked.connect(self._delete_current)
        self._refresh_btn.clicked.connect(self.reload)
        self.reload()

    def reload(self) -> None:
        self._records = self._store.list_records()
        self._list.clear()
        for rec in self._records:
            if rec.status == STATUS_READ_ERROR:
                text = f"[读取异常] {rec.record_id[:8]}（已隔离，可删除）"
            else:
                mark = " [未保存]" if rec.status == STATUS_SAVE_FAILED else ""
                text = f"{rec.updated_at} · {rec.input_method}{mark}\n{rec.edited_latex[:60]}"
            item = QListWidgetItem(text)
            self._list.addItem(item)
        total = self._store.total_size_bytes()
        free = self._store.disk_free_bytes()
        self._info_label.setText(
            f"历史目录：{self._store.base_dir}\n"
            f"占用 {total / 1024 / 1024:.1f} MB · 磁盘剩余 {free / 1024 / 1024 / 1024:.1f} GB"
        )

    def current_record(self) -> HistoryRecord | None:
        row = self._list.currentRow()
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def _open_current(self) -> None:
        rec = self.current_record()
        if rec is None:
            return
        if rec.status == STATUS_READ_ERROR:
            QMessageBox.warning(
                self, "记录损坏", "该记录已损坏并被隔离，无法打开。可删除该记录。"
            )
            return
        self.recordOpenRequested.emit(rec)

    def _delete_current(self) -> None:
        rec = self.current_record()
        if rec is None:
            return
        answer = QMessageBox.question(
            self,
            "确认删除",
            "删除该记录及其图片副本？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._store.delete_record(rec):
            self.recordDeleted.emit()
            self.reload()
        else:
            QMessageBox.warning(
                self, "删除失败", "文件删除失败，记录未删除。可稍后重试。"
            )
