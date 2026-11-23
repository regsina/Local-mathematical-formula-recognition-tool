import time

from PySide6.QtGui import QImage

from .base import RecognitionResult, Recognizer

DEMO_LATEX = r"p_{\mathrm{RAG-Sequence}}(y\mid x) \approx \sum_{z} p_{\eta}(z\mid x)\,p_{\theta}(y\mid x,z)"


class PlaceholderRecognizer(Recognizer):
    def __init__(self, delay_s: float = 1.5):
        self._delay = delay_s

    def name(self) -> str:
        return "placeholder"

    def version(self) -> str:
        return "0.0.0-placeholder"

    def is_ready(self) -> bool:
        return True

    def recognize(self, image: QImage, should_stop) -> RecognitionResult:
        steps = max(int(self._delay * 10), 1)
        for _ in range(steps):
            if should_stop():
                raise InterruptedError("cancelled")
            time.sleep(0.1)
        return RecognitionResult(
            latex=DEMO_LATEX,
            model_name=self.name(),
            model_version=self.version(),
        )
