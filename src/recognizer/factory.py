from .base import Recognizer
from .placeholder import PlaceholderRecognizer


def create_default_recognizer() -> Recognizer:
    try:
        from .unimernet import UniMERNetRecognizer

        recognizer = UniMERNetRecognizer()
        if recognizer.is_ready():
            return recognizer
    except Exception:
        pass
    return PlaceholderRecognizer()
