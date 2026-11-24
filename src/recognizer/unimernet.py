import argparse
import os
import tempfile

from PySide6.QtGui import QImage

from .. import config
from .base import RecognitionResult, Recognizer

_YAML_TEMPLATE = """model:
  arch: unimernet
  model_type: unimernet
  model_config:
    model_name: "{model_dir}"
    max_seq_len: 1536
  load_pretrained: True
  pretrained: "{model_dir}/unimernet_small.pth"
  tokenizer_config:
    path: "{model_dir}"

datasets:
  formula_rec_eval:
    vis_processor:
      eval:
        name: "formula_image_eval"
        image_size:
          - 192
          - 672

run:
  runner: runner_iter
  task: unimernet_train
  batch_size_train: 64
  batch_size_eval: 64
  num_workers: 1
  iters_per_inner_epoch: 2000
  max_iters: 60000
  seed: 42
  output_dir: "output/demo"
  evaluate: True
  test_splits: [ "eval" ]
  device: "cuda"
  world_size: 1
  dist_url: "env://"
  distributed: True
  distributed_type: ddp
  generate_cfg:
    temperature: 0.0
"""

WEIGHTS_FILE = "unimernet_small.pth"


def _qimage_to_pil(image: QImage):
    from PIL import Image

    img = image.convertToFormat(QImage.Format.Format_RGB888)
    ptr = img.bits()
    data = bytes(ptr[: img.sizeInBytes()])
    return Image.frombytes("RGB", (img.width(), img.height()), data)


class UniMERNetRecognizer(Recognizer):
    def __init__(self, model_dir: str | None = None):
        self._model_dir = model_dir or os.path.join(
            config.model_dir(), "unimernet_small"
        )
        self._model = None
        self._vis_processor = None
        self._device = None

    def name(self) -> str:
        return "unimernet"

    def version(self) -> str:
        return "small-0.2.3"

    def is_ready(self) -> bool:
        return os.path.isfile(os.path.join(self._model_dir, WEIGHTS_FILE))

    def _write_runtime_yaml(self) -> str:
        model_dir = os.path.abspath(self._model_dir).replace("\\", "/")
        content = _YAML_TEMPLATE.format(model_dir=model_dir)
        fd, path = tempfile.mkstemp(prefix="unimernet_demo_", suffix=".yaml")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from unimernet import tasks
        from unimernet.common.config import Config
        from unimernet.processors import load_processor

        yaml_path = self._write_runtime_yaml()
        try:
            args = argparse.Namespace(cfg_path=yaml_path, options=None)
            cfg = Config(args)
            task = tasks.setup_task(cfg)
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = task.build_model(cfg).to(self._device)
            self._model.eval()
            self._vis_processor = load_processor(
                "formula_image_eval",
                cfg.config.datasets.formula_rec_eval.vis_processor.eval,
            )
        finally:
            try:
                os.unlink(yaml_path)
            except OSError:
                pass

    def recognize(self, image: QImage, should_stop) -> RecognitionResult:
        if should_stop():
            raise InterruptedError("cancelled")
        if not self.is_ready():
            raise RuntimeError(
                f"模型文件缺失：{os.path.join(self._model_dir, WEIGHTS_FILE)}"
            )
        self._ensure_loaded()
        if should_stop():
            raise InterruptedError("cancelled")
        pil_image = _qimage_to_pil(image)
        import torch

        tensor = self._vis_processor(pil_image).unsqueeze(0).to(self._device)
        with torch.no_grad():
            output = self._model.generate({"image": tensor})
        if should_stop():
            raise InterruptedError("cancelled")
        latex = str(output["pred_str"][0]).strip()
        if not latex:
            raise RuntimeError("模型输出为空")
        return RecognitionResult(
            latex=latex, model_name=self.name(), model_version=self.version()
        )
