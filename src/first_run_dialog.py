import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from . import config
from .env_check import blocking_failures, run_all_checks

MARKER_FILE = "first_run_done.marker"


def first_run_completed() -> bool:
    return os.path.exists(os.path.join(config.data_dir(), MARKER_FILE))


def mark_first_run_completed() -> None:
    os.makedirs(config.data_dir(), exist_ok=True)
    with open(os.path.join(config.data_dir(), MARKER_FILE), "w", encoding="utf-8") as f:
        f.write("done")


class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("首次运行准备")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("正在检查运行环境（先检查环境，再决定是否下载模型）："))
        self._check_label = QLabel("检查中…")
        self._check_label.setTextFormat(Qt.TextFormat.PlainText)
        self._check_label.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self._check_label, 1)
        self._model_label = QLabel()
        self._model_label.setWordWrap(True)
        layout.addWidget(self._model_label)
        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self._buttons.accepted.connect(self.accept)
        layout.addWidget(self._buttons)
        self._run_checks()

    def _run_checks(self) -> None:
        items = run_all_checks()
        lines = []
        for item in items:
            mark = "[通过]" if item.ok else "[未通过]"
            lines.append(f"{mark} {item.name}：{item.detail}")
        self._check_label.setText("\n".join(lines))
        blockers = blocking_failures(items)
        if blockers:
            self._model_label.setText(
                "基础运行环境不满足，已按规则中止模型下载准备。请修复上述问题后重新启动。"
            )
            self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        else:
            self._model_label.setText(
                "模型准备：当前版本使用占位识别器进行流程验证，"
                "UniMERNet 模型将在 G1 技术基线冻结后接入（PRD 11.1）。"
                "准备完成后应用可离线运行。"
            )
