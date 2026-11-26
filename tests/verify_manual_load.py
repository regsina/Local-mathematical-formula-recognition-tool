import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src.recognizer.paddleocr_vl import PaddleOCRVLRecognizer

rec = PaddleOCRVLRecognizer()
t0 = time.time()
rec._ensure_loaded()
print(f"load ok: {time.time() - t0:.1f}s, device={rec._device}")
print("processor:", type(rec._processor).__name__)

img = QImage(os.path.join("tests", "eval_real", "Snipaste_2026-11-24_14-40-48.png"))
t1 = time.time()
out = rec.recognize(img, lambda: False)
print(f"recognize ok: {time.time() - t1:.2f}s")
print("latex:", out.latex)
