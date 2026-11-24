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

GROUND_TRUTH = {
    "rag_sequence": r"p_{\mathrm{RAG-Sequence}}(y\mid x) \approx \sum_{z} p_{\eta}(z\mid x)\,p_{\theta}(y\mid x,z)",
    "fraction": r"\frac{x+1}{x-1}",
    "sqrt": r"\sqrt{x^2+1}",
    "sum_limit": r"\sum_{i=1}^{N} x_i^2",
    "subscript": r"a_n + b_{n-1}",
    "greek": r"\alpha^2 + \beta \cdot \gamma \approx \theta",
}


def main() -> None:
    rec = UniMERNetRecognizer()
    print("model ready:", rec.is_ready())

    t0 = time.time()
    rec._ensure_loaded()
    load_s = time.time() - t0
    print(f"model load time: {load_s:.2f}s, device: {rec._device}")

    try:
        import torch

        if torch.cuda.is_available():
            print(f"gpu name: {torch.cuda.get_device_name(0)}")
            print(
                f"gpu mem after load: {torch.cuda.memory_allocated(0) / 1024**2:.0f} MiB"
            )
    except Exception as e:
        print("gpu info unavailable:", e)

    results = {}
    for name in sorted(GROUND_TRUTH):
        path = os.path.join(SAMPLE_DIR, f"{name}.png")
        img = QImage(path)
        t1 = time.time()
        try:
            out = rec.recognize(img, lambda: False)
            dt = time.time() - t1
            results[name] = (True, out.latex, dt)
            print(f"[{name}] {dt:.2f}s")
            print(f"  pred: {out.latex}")
            print(f"  gt  : {GROUND_TRUTH[name]}")
        except Exception as e:
            dt = time.time() - t1
            results[name] = (False, str(e), dt)
            print(f"[{name}] FAILED {dt:.2f}s: {e}")

    try:
        import torch

        if torch.cuda.is_available():
            print(
                f"gpu mem peak: {torch.cuda.max_memory_allocated(0) / 1024**2:.0f} MiB"
            )
    except Exception:
        pass

    ok = sum(1 for v in results.values() if v[0])
    print(f"\nSUMMARY: {ok}/{len(results)} succeeded")


if __name__ == "__main__":
    main()
