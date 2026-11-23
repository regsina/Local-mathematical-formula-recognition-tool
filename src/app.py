import sys

from PySide6.QtWidgets import QApplication

from . import config
from .first_run_dialog import (
    FirstRunDialog,
    first_run_completed,
    mark_first_run_completed,
)
from .main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationDisplayName(config.APP_DISPLAY_NAME)
    config.ensure_dirs()
    if not first_run_completed():
        dialog = FirstRunDialog()
        if dialog.exec() != FirstRunDialog.DialogCode.Accepted:
            return 0
        mark_first_run_completed()
    window = MainWindow()
    window.show()
    return app.exec()
