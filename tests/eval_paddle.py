import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src.recognizer.paddleocr_vl import PaddleOCRVLRecognizer
from src.renderer import render_latex

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_real")


def main() -> None:
    rec = PaddleOCRVLRecognizer()
    print("model ready:", rec.is_ready())
    t0 = time.time()
    rec._ensure_loaded()
    print(f"load time: {time.time() - t0:.1f}s, device: {rec._device}")

    results = {}
    images = sorted(
        f for f in os.listdir(EVAL_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )
    for fname in images:
        img = QImage(os.path.join(EVAL_DIR, fname))
        t1 = time.time()
        try:
            out = rec.recognize(img, lambda: False)
            pred = out.latex
            err = ""
        except Exception as e:
            pred = ""
            err = str(e)
        dt = time.time() - t1
        renderable = bool(pred) and render_latex(pred).ok
        results[fname] = {
            "pred": pred,
            "error": err,
            "time": dt,
            "renderable": renderable,
        }
        status = "OK " if (pred and renderable) else ("NORENDER" if pred else "FAIL")
        print(f"[{status}] {fname} ({dt:.2f}s)")

    path = os.path.join(EVAL_DIR, "predictions_paddleocr_vl.txt")
    with open(path, "w", encoding="utf-8") as f:
        for fname, r in results.items():
            f.write(f"### {fname} ({r['time']:.2f}s)\n")
            f.write(f"{r['pred'] or 'ERROR: ' + r['error']}\n\n")
    print(f"saved {path}")

    total = len(results)
    recognized = sum(1 for r in results.values() if r["pred"])
    renderable = sum(1 for r in results.values() if r["renderable"])
    times = [r["time"] for r in results.values()]
    print(f"\n识别成功 {recognized}/{total}，可渲染 {renderable}/{total}")
    if times:
        print(f"耗时 avg {sum(times) / len(times):.2f}s, max {max(times):.2f}s")


if __name__ == "__main__":
    main()
