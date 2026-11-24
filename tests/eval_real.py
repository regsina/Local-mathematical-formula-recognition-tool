import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src import config
from src.recognizer.unimernet import UniMERNetRecognizer
from src.renderer import render_latex

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_real")


def run_model(model_dir_name: str) -> dict:
    rec = UniMERNetRecognizer(
        model_dir=os.path.join(config.model_dir(), model_dir_name)
    )
    if not rec.is_ready():
        print(f"[{model_dir_name}] 模型未就绪，跳过")
        return {}
    t0 = time.time()
    rec._ensure_loaded()
    print(f"[{model_dir_name}] 加载耗时 {time.time() - t0:.1f}s")

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
        renderable = False
        if pred:
            renderable = render_latex(pred).ok
        results[fname] = {
            "pred": pred,
            "error": err,
            "time": dt,
            "renderable": renderable,
        }
        status = "OK " if (pred and renderable) else ("NORENDER" if pred else "FAIL")
        print(f"  [{status}] {fname} ({dt:.2f}s)")
    return results


def save_predictions(model_name: str, results: dict) -> None:
    path = os.path.join(EVAL_DIR, f"predictions_{model_name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for fname, r in results.items():
            f.write(f"### {fname} ({r['time']:.2f}s)\n")
            f.write(f"{r['pred'] or 'ERROR: ' + r['error']}\n\n")
    print(f"saved {path}")


def summarize(model_name: str, results: dict) -> None:
    total = len(results)
    recognized = sum(1 for r in results.values() if r["pred"])
    renderable = sum(1 for r in results.values() if r["renderable"])
    times = [r["time"] for r in results.values()]
    print(
        f"\n[{model_name}] 识别成功 {recognized}/{total}，可渲染 {renderable}/{total}"
    )
    if times:
        print(
            f"[{model_name}] 耗时 avg {sum(times) / len(times):.2f}s, max {max(times):.2f}s"
        )


def main() -> None:
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
        results = run_model(model_name)
        if results:
            save_predictions(model_name, results)
            summarize(model_name, results)
        return

    all_results = {}
    for model_name in ["unimernet_small", "unimernet_base"]:
        results = run_model(model_name)
        if results:
            save_predictions(model_name, results)
            summarize(model_name, results)
            all_results[model_name] = results
        import gc

        import torch

        del results
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if len(all_results) == 2:
        small, base = all_results["unimernet_small"], all_results["unimernet_base"]
        better = sum(
            1
            for f in small
            if base.get(f, {}).get("renderable") and not small[f]["renderable"]
        )
        print(f"\nbase 相比 small 可渲染性提升的样本数: {better}/{len(small)}")


if __name__ == "__main__":
    main()
