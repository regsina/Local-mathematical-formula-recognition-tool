from .base import Recognizer
from .placeholder import PlaceholderRecognizer


def create_default_recognizer() -> Recognizer:
    return PlaceholderRecognizer()
