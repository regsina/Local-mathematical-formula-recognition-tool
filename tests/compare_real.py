import os
import re

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_real")


def normalize(text: str) -> str:
    t = text
    t = t.replace("\\[", "").replace("\\]", "")
    t = re.sub(
        r"\\(mathrm|operatorname|text|mathbf|boldsymbol|mathsf|mathfrak)\s*\*?\s*{([^}]*)}",
        r"\2",
        t,
    )
    t = re.sub(r"\\(quad|,|;|!| )", "", t)
    t = t.replace("\\limits", "")
    t = t.replace("\\left", "").replace("\\right", "")
    t = t.replace("\\prime", "'")
    t = t.replace("\\to", "\\rightarrow")
    t = re.sub(r"\s+", "", t)
    return t


def load_predictions(model: str) -> dict:
    path = os.path.join(EVAL_DIR, f"predictions_{model}.txt")
    preds = {}
    if not os.path.exists(path):
        return preds
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for block in content.split("### ")[1:]:
        lines = block.strip().splitlines()
        header = lines[0]
        fname = header.split(" (")[0].strip()
        pred = " ".join(lines[1:]).strip()
        preds[fname] = pred
    return preds


def main() -> None:
    gt = {}
    with open(os.path.join(EVAL_DIR, "ground_truth.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            fname, latex = line.split("\t", 1)
            gt[fname] = latex

    for model in ["paddleocr_vl", "unimernet_base", "unimernet_small"]:
        preds = load_predictions(model)
        if not preds:
            continue
        exact = 0
        diff = []
        for fname in sorted(gt):
            p = preds.get(fname, "")
            g = gt[fname]
            if p and normalize(p) == normalize(g):
                exact += 1
            else:
                diff.append(fname)
        print(f"[{model}] 规范化精确匹配: {exact}/{len(gt)}")
        print(f"  待人工核对差异样本: {len(diff)}")
        for fname in diff:
            print(f"\n### {fname}")
            print(f"  GT  : {gt[fname]}")
            print(f"  PRED: {preds.get(fname, '')}")
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
