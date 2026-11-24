import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src.recognizer.unimernet import UniMERNetRecognizer

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_set")


def normalize(text: str) -> str:
    t = re.sub(r"\\(mathrm|operatorname|text|mathbf)\s*\*?\s*{([^}]*)}", r"\2", text)
    t = re.sub(r"\\,", "", t)
    t = re.sub(r"\\;", "", t)
    t = re.sub(r"\\ ", " ", t)
    t = re.sub(r"\s+", "", t)
    t = t.replace("\\limits", "")
    t = t.replace("\\left", "").replace("\\right", "")
    return t


def main() -> None:
    rec = UniMERNetRecognizer()
    rec._ensure_loaded()

    gt = {}
    with open(os.path.join(EVAL_DIR, "ground_truth.txt"), encoding="utf-8") as f:
        for line in f:
            name, latex = line.rstrip("\n").split("\t", 1)
            gt[name] = latex

    exact = 0
    total = 0
    fails = []
    times = []
    for name in sorted(gt):
        path = os.path.join(EVAL_DIR, f"{name}.png")
        if not os.path.exists(path):
            continue
        total += 1
        img = QImage(path)
        t0 = time.time()
        try:
            out = rec.recognize(img, lambda: False)
            pred = out.latex
        except Exception as e:
            pred = f"ERROR: {e}"
        dt = time.time() - t0
        times.append(dt)
        same = normalize(pred) == normalize(gt[name])
        if same:
            exact += 1
        else:
            fails.append((name, gt[name], pred))
        mark = "OK " if same else "DIFF"
        print(f"[{mark}] {name} ({dt:.2f}s)")

    print()
    for name, g, p in fails:
        print(f"--- {name}")
        print(f"  gt  : {g}")
        print(f"  pred: {p}")
    print()
    print(f"normalized-exact: {exact}/{total} = {exact / total * 100:.1f}%")
    if times:
        print(f"time avg {sum(times) / len(times):.2f}s, max {max(times):.2f}s")


if __name__ == "__main__":
    main()
