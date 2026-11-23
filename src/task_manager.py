import itertools

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage

from .recognizer.base import Recognizer

STATE_IDLE = "idle"
STATE_RECOGNIZING = "recognizing"
STATE_CANCELLING = "cancelling"


class _Worker(QThread):
    succeeded = Signal(int, str, str, str)
    failed = Signal(int, str)

    def __init__(
        self, recognizer: Recognizer, task_id: int, image: QImage, parent=None
    ):
        super().__init__(parent)
        self._recognizer = recognizer
        self._task_id = task_id
        self._image = image
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            result = self._recognizer.recognize(self._image, lambda: self._stop)
            self.succeeded.emit(
                self._task_id, result.latex, result.model_name, result.model_version
            )
        except InterruptedError:
            self.failed.emit(self._task_id, "cancelled")
        except Exception as exc:
            self.failed.emit(self._task_id, str(exc) or "识别失败")


class TaskManager(QObject):
    stateChanged = Signal(str)
    recognizeSucceeded = Signal(int, str, str, str)
    recognizeFailed = Signal(int, str)
    cancelFinished = Signal()

    def __init__(self, recognizer: Recognizer, parent=None):
        super().__init__(parent)
        self._recognizer = recognizer
        self._state = STATE_IDLE
        self._worker = None
        self._current_task_id = 0
        self._id_counter = itertools.count(1)

    @property
    def state(self) -> str:
        return self._state

    def is_busy(self) -> bool:
        return self._state != STATE_IDLE

    def start(self, image: QImage) -> int:
        if self.is_busy():
            return 0
        task_id = next(self._id_counter)
        self._current_task_id = task_id
        self._worker = _Worker(self._recognizer, task_id, image, self)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._set_state(STATE_RECOGNIZING)
        self._worker.start()
        return task_id

    def cancel(self) -> None:
        if self._state != STATE_RECOGNIZING or self._worker is None:
            return
        self._worker.request_stop()
        self._set_state(STATE_CANCELLING)

    def _on_succeeded(
        self, task_id: int, latex: str, model_name: str, model_version: str
    ) -> None:
        current = self._current_task_id
        self._finish_worker()
        if self._state == STATE_CANCELLING or task_id != current:
            self._set_state(STATE_IDLE)
            self.cancelFinished.emit()
            return
        self._set_state(STATE_IDLE)
        self.recognizeSucceeded.emit(task_id, latex, model_name, model_version)

    def _on_failed(self, task_id: int, reason: str) -> None:
        current = self._current_task_id
        was_cancelling = self._state == STATE_CANCELLING
        self._finish_worker()
        self._set_state(STATE_IDLE)
        if was_cancelling or task_id != current or reason == "cancelled":
            self.cancelFinished.emit()
            return
        self.recognizeFailed.emit(task_id, reason)

    def _finish_worker(self) -> None:
        if self._worker is not None:
            self._worker.wait(5000)
            self._worker.deleteLater()
            self._worker = None

    def _set_state(self, state: str) -> None:
        if self._state != state:
            self._state = state
            self.stateChanged.emit(state)
