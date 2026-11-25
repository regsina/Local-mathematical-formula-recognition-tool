import os

APP_NAME = "LocalFormulaRecognition"
APP_DISPLAY_NAME = "本地数学公式识别工具"

# 以下阈值已于 G2 冻结（依据《开发需求/G1技术验证记录.md》实测数据）
# O03 模型路线：PaddleOCR-VL-0.9B（x2 预处理，真实验收集可用率 93%~97%）
# O04 输入上限：流程验证可用，冻结为下列值
# O05 性能口径：x2 预处理后 avg 1.47s，满足约 5 秒目标
AUTOSAVE_DEBOUNCE_MS = 1000
PREVIEW_DEBOUNCE_MS = 1000
RENDER_TIMEOUT_S = 3
MAX_SOURCE_CHARS = 4000
MAX_IMAGE_PIXELS = 40_000_000
MAX_FILE_BYTES = 30 * 1024 * 1024
CANVAS_EXPORT_WIDTH = 960
CANVAS_EXPORT_HEIGHT = 540
MODEL_DIR_NAME = "models"
HISTORY_DIR_NAME = "history"
META_FILE_NAME = "meta.json"
INPUT_IMAGE_NAME = "input.png"
ORIGINAL_FILE_NAME = "original"


def data_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def history_dir() -> str:
    return os.path.join(data_dir(), HISTORY_DIR_NAME)


def model_dir() -> str:
    return os.path.join(data_dir(), MODEL_DIR_NAME)


def ensure_dirs() -> None:
    os.makedirs(history_dir(), exist_ok=True)
    os.makedirs(model_dir(), exist_ok=True)
