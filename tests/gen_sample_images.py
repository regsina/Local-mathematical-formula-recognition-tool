import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

SAMPLES = {
    "rag_sequence": r"p_{\mathrm{RAG-Sequence}}(y\mid x) \approx \sum_{z} p_{\eta}(z\mid x)\,p_{\theta}(y\mid x,z)",
    "fraction": r"\frac{x+1}{x-1}",
    "sqrt": r"\sqrt{x^2+1}",
    "sum_limit": r"\sum_{i=1}^{N} x_i^2",
    "subscript": r"a_n + b_{n-1}",
    "greek": r"\alpha^2 + \beta \cdot \gamma \approx \theta",
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_images")


def render_to_file(latex: str, path: str) -> None:
    fig = plt.figure(figsize=(0.01, 0.01))
    text = fig.text(0, 0, f"${latex}$", fontsize=20)
    fig.canvas.draw()
    bbox = text.get_window_extent()
    plt.close(fig)
    w, h = int(bbox.width) + 24, int(bbox.height) + 24
    fig = plt.figure(figsize=(w / 100.0, h / 100.0), dpi=100)
    fig.text(12 / w, 12 / h, f"${latex}$", fontsize=20)
    fig.savefig(path, dpi=100, facecolor="white")
    plt.close(fig)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, latex in SAMPLES.items():
        path = os.path.join(OUT_DIR, f"{name}.png")
        render_to_file(latex, path)
        print("saved", path)


if __name__ == "__main__":
    main()
