import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src.recognizer.paddleocr_vl import PaddleOCRVLRecognizer

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_real")

FAILED = [
    "Snipaste_2026-11-24_14-40-16.png",
    "Snipaste_2026-11-24_14-41-04.png",
    "Snipaste_2026-11-24_14-41-23.png",
    "Snipaste_2026-11-24_14-41-38.png",
    "Snipaste_2026-11-24_14-42-10.png",
    "Snipaste_2026-11-24_14-42-51.png",
    "Snipaste_2026-11-24_14-42-56.png",
]

GT = {}
with open(os.path.join(EVAL_DIR, "ground_truth.txt"), encoding="utf-8") as f:
    for line in f:
        fname, latex = line.rstrip("\n").split("\t", 1)
        GT[fname] = latex


def scale_image(img: QImage, factor: float, pad: int) -> QImage:
    w = int(img.width() * factor)
    h = int(img.height() * factor)
    scaled = img.scaled(w, h)
    if pad <= 0:
        return scaled
    out = QImage(w + pad * 2, h + pad * 2, QImage.Format.Format_RGB888)
    from PySide6.QtGui import QColor, QPainter

    out.fill(QColor(255, 255, 255))
    p = QPainter(out)
    p.drawImage(pad, pad, scaled)
    p.end()
    return out


def main() -> None:
    rec = PaddleOCRVLRecognizer()
    rec._ensure_loaded()

    strategies = {
        "orig": lambda img: img,
        "x2": lambda img: scale_image(img, 2.0, 0),
        "x2_pad": lambda img: scale_image(img, 2.0, 40),
        "x3_pad": lambda img: scale_image(img, 3.0, 60),
    }

    for fname in FAILED:
        img = QImage(os.path.join(EVAL_DIR, fname))
        print(f"\n{'=' * 70}\n{fname}  ({img.width()}x{img.height()})")
        print(f"  GT: {GT[fname]}")
        for sname, fn in strategies.items():
            t0 = time.time()
            try:
                out = rec.recognize(fn(img), lambda: False)
                pred = out.latex
            except Exception as e:
                pred = f"ERROR: {e}"
            print(f"  [{sname}] ({time.time() - t0:.1f}s) {pred}")


if __name__ == "__main__":
    main()
