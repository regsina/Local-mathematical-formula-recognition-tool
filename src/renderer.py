from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt
from PySide6.QtGui import QImage

from . import config


@dataclass
class RenderResult:
    image: QImage | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.image is not None


def _render_sync(latex: str) -> QImage:
    fig = plt.figure(figsize=(0.01, 0.01))
    try:
        text = fig.text(0, 0, f"${latex}$", fontsize=16)
        fig.canvas.draw()
        bbox = text.get_window_extent()
        w, h = int(bbox.width) + 20, int(bbox.height) + 20
        plt.close(fig)
        fig = plt.figure(figsize=(w / 100.0, h / 100.0), dpi=100)
        fig.text(10 / w, 10 / h, f"${latex}$", fontsize=16)
        fig.canvas.draw()
        buf = fig.canvas.buffer_rgba()
        image = QImage(buf, w, h, QImage.Format.Format_RGBA8888).copy()
        return image
    finally:
        plt.close(fig)


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="latex-render")


def render_latex(latex: str) -> RenderResult:
    source = latex.strip()
    if not source:
        return RenderResult(image=None, error="空源码")
    if len(source) > config.MAX_SOURCE_CHARS:
        return RenderResult(
            image=None,
            error=f"源码超过长度上限（{config.MAX_SOURCE_CHARS} 字符，拟定值，G1 冻结）",
        )
    future = _executor.submit(_render_sync, source)
    try:
        image = future.result(timeout=config.RENDER_TIMEOUT_S)
        return RenderResult(image=image)
    except FutureTimeout:
        return RenderResult(
            image=None,
            error=f"渲染超时（{config.RENDER_TIMEOUT_S} 秒，拟定值，G1 冻结）",
        )
    except Exception as exc:
        return RenderResult(image=None, error=f"渲染失败：{exc}")
