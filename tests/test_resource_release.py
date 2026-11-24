import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src.recognizer.unimernet import UniMERNetRecognizer

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_images")
ROUNDS = 10


def main() -> None:
    import torch

    rec = UniMERNetRecognizer()
    rec._ensure_loaded()
    img = QImage(os.path.join(SAMPLE_DIR, "fraction.png"))

    print(f"device: {rec._device}")
    baseline = torch.cuda.memory_allocated(0) if torch.cuda.is_available() else 0
    print(f"baseline mem: {baseline / 1024**2:.0f} MiB")

    readings = []
    for i in range(ROUNDS):
        t0 = time.time()
        out = rec.recognize(img, lambda: False)
        dt = time.time() - t0
        mem = torch.cuda.memory_allocated(0) if torch.cuda.is_available() else 0
        peak = torch.cuda.max_memory_allocated(0) if torch.cuda.is_available() else 0
        readings.append(mem)
        print(
            f"round {i + 1}: {dt:.2f}s, mem {mem / 1024**2:.0f} MiB, peak {peak / 1024**2:.0f} MiB"
        )

    if readings:
        growth = readings[-1] - readings[0]
        print(
            f"\nmem first: {readings[0] / 1024**2:.0f} MiB, last: {readings[-1] / 1024**2:.0f} MiB, growth: {growth / 1024**2:.1f} MiB"
        )
        if growth < 50 * 1024 * 1024:
            print("RESOURCE RELEASE: PASS (no continuous growth)")
        else:
            print("RESOURCE RELEASE: FAIL (continuous growth detected)")


if __name__ == "__main__":
    main()
