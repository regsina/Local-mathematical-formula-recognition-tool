import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from src import config

os.environ.setdefault("HF_HOME", os.path.join(config.data_dir(), "hf_cache"))

model_dir = os.path.join(config.model_dir(), "paddleocr_vl")
print("model_dir:", model_dir)
print("exists:", os.path.isdir(model_dir))

from transformers import AutoProcessor

try:
    processor = AutoProcessor.from_pretrained(model_dir, trust_remote_code=True)
    print("processor type:", type(processor))
    print("processor is None:", processor is None)
    print("has apply_chat_template:", hasattr(processor, "apply_chat_template"))
except Exception:
    import traceback

    traceback.print_exc()
