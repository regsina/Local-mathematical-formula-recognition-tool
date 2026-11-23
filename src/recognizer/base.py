from abc import ABC, abstractmethod
from dataclasses import dataclass

from PySide6.QtGui import QImage


@dataclass
class RecognitionResult:
    latex: str
    model_name: str
    model_version: str


class Recognizer(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    def recognize(self, image: QImage, should_stop) -> RecognitionResult: ...
