import os

from PySide6.QtGui import QImage

from .. import config
from .base import RecognitionResult, Recognizer

MODEL_SUBDIR = "paddleocr_vl"
FORMULA_PROMPT = "Formula Recognition:"
PREPROCESS_SCALE = 2.0


def _qimage_to_pil(image: QImage):
    from PIL import Image

    img = image.convertToFormat(QImage.Format.Format_RGB888)
    ptr = img.bits()
    data = bytes(ptr[: img.sizeInBytes()])
    return Image.frombytes("RGB", (img.width(), img.height()), data)


class PaddleOCRVLRecognizer(Recognizer):
    def __init__(self, model_dir: str | None = None):
        self._model_dir = model_dir or os.path.join(config.model_dir(), MODEL_SUBDIR)
        self._model = None
        self._processor = None
        self._device = None

    def name(self) -> str:
        return "paddleocr_vl"

    def version(self) -> str:
        return "0.9B-2025.10"

    def is_ready(self) -> bool:
        return os.path.isfile(os.path.join(self._model_dir, "model.safetensors"))

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        os.environ.setdefault("HF_HOME", os.path.join(config.data_dir(), "hf_cache"))
        os.makedirs(os.environ["HF_HOME"], exist_ok=True)
        import sys

        import torch

        pkg_parent = os.path.dirname(self._model_dir)
        pkg_name = os.path.basename(self._model_dir)
        init_file = os.path.join(self._model_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8"):
                pass
        if pkg_parent not in sys.path:
            sys.path.insert(0, pkg_parent)
        modeling = __import__(
            f"{pkg_name}.modeling_paddleocr_vl",
            fromlist=["PaddleOCRVLForConditionalGeneration"],
        )
        processing = __import__(
            f"{pkg_name}.processing_paddleocr_vl", fromlist=["PaddleOCRVLProcessor"]
        )
        model_cls = modeling.PaddleOCRVLForConditionalGeneration
        processor_cls = processing.PaddleOCRVLProcessor

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = (
            model_cls.from_pretrained(
                self._model_dir,
                torch_dtype=torch.bfloat16,
            )
            .to(self._device)
            .eval()
        )
        self._processor = processor_cls.from_pretrained(
            self._model_dir, trust_remote_code=True
        )

    def recognize(self, image: QImage, should_stop) -> RecognitionResult:
        if should_stop():
            raise InterruptedError("cancelled")
        if not self.is_ready():
            raise RuntimeError(
                f"模型文件缺失：{os.path.join(self._model_dir, 'model.safetensors')}"
            )
        self._ensure_loaded()
        if should_stop():
            raise InterruptedError("cancelled")
        import torch

        scaled = image
        if PREPROCESS_SCALE != 1.0:
            from PySide6.QtCore import Qt

            scaled = image.scaled(
                int(image.width() * PREPROCESS_SCALE),
                int(image.height() * PREPROCESS_SCALE),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        pil_image = _qimage_to_pil(scaled)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": FORMULA_PROMPT},
                ],
            }
        ]
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._device)
        with torch.inference_mode():
            output = self._model.generate(
                **inputs, max_new_tokens=1024, do_sample=False, use_cache=True
            )
        if should_stop():
            raise InterruptedError("cancelled")
        text = self._processor.batch_decode(output, skip_special_tokens=True)[0]
        latex = text.strip()
        if "Assistant:" in latex:
            latex = latex.split("Assistant:", 1)[1].strip()
        elif "Formula Recognition:" in latex:
            latex = latex.split("Formula Recognition:", 1)[1].strip()
        latex = latex.removeprefix("User:").strip()
        if latex.startswith("\\[") and latex.endswith("\\]"):
            latex = latex[2:-2].strip()
        if latex.startswith("$$") and latex.endswith("$$"):
            latex = latex[2:-2].strip()
        if latex.startswith("$") and latex.endswith("$"):
            latex = latex[1:-1].strip()
        if not latex:
            raise RuntimeError("模型输出为空")
        return RecognitionResult(
            latex=latex, model_name=self.name(), model_version=self.version()
        )
