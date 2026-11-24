import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

EVAL_SET = {
    "frac_01": r"\frac{x+1}{x-1}",
    "frac_02": r"\frac{a}{b} + \frac{c}{d}",
    "frac_03": r"\frac{\partial f}{\partial x}",
    "frac_04": r"\frac{1}{1+x^2}",
    "frac_05": r"\frac{n!}{k!(n-k)!}",
    "frac_06": r"\frac{-b \pm \sqrt{b^2-4ac}}{2a}",
    "sqrt_01": r"\sqrt{x^2+1}",
    "sqrt_02": r"\sqrt[3]{27}",
    "sqrt_03": r"\sqrt{\frac{a}{b}}",
    "sqrt_04": r"\sqrt{a} + \sqrt{b}",
    "sqrt_05": r"\frac{1}{\sqrt{2\pi}} e^{-\frac{x^2}{2}}",
    "sum_01": r"\sum_{i=1}^{N} x_i^2",
    "sum_02": r"\prod_{k=1}^{n} k = n!",
    "sum_03": r"\int_0^1 x^2 dx",
    "sum_04": r"\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}",
    "sum_05": r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
    "sum_06": r"\sum_{n=0}^{\infty} \frac{x^n}{n!} = e^x",
    "sub_01": r"a_n + b_{n-1}",
    "sub_02": r"x_i^2 + y_j^3",
    "sub_03": r"e^{i\pi} + 1 = 0",
    "sub_04": r"a_1^2 + a_2^2 + \cdots + a_n^2",
    "greek_01": r"\alpha^2 + \beta \cdot \gamma \approx \theta",
    "greek_02": r"\alpha + \beta = \gamma",
    "greek_03": r"\Delta = b^2 - 4ac",
    "greek_04": r"\pi r^2",
    "greek_05": r"\forall \epsilon > 0, \exists \delta > 0",
    "greek_06": r"A \cup B, A \cap B",
    "greek_07": r"x \leq y \Rightarrow x + z \leq y + z",
    "long_01": r"p_{\mathrm{RAG-Sequence}}(y\mid x) \approx \sum_{z} p_{\eta}(z\mid x)\,p_{\theta}(y\mid x,z)",
    "long_02": r"(a+b)^n = \sum_{k=0}^{n} \binom{n}{k} a^{n-k} b^k",
    "long_03": r"f(x) = a_0 + \sum_{n=1}^{\infty} \left( a_n \cos \frac{n\pi x}{L} + b_n \sin \frac{n\pi x}{L} \right)",
    "long_04": r"e^x = \sum_{n=0}^{\infty} \frac{x^n}{n!}",
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_set")


def render_to_file(latex: str, path: str) -> bool:
    try:
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
        return True
    except Exception as exc:
        print("SKIP render fail:", path, exc)
        return False


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    gt_path = os.path.join(OUT_DIR, "ground_truth.txt")
    saved = []
    with open(gt_path, "w", encoding="utf-8") as f:
        for name, latex in EVAL_SET.items():
            path = os.path.join(OUT_DIR, f"{name}.png")
            if render_to_file(latex, path):
                f.write(f"{name}\t{latex}\n")
                saved.append(name)
    print(f"generated {len(saved)}/{len(EVAL_SET)} images -> {OUT_DIR}")


if __name__ == "__main__":
    main()
