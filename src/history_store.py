import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtGui import QImage

from . import config

STATUS_NORMAL = "normal"
STATUS_SAVE_FAILED = "save_failed"
STATUS_READ_ERROR = "read_error"


@dataclass
class HistoryRecord:
    record_id: str
    created_at: str
    updated_at: str
    input_method: str
    raw_latex: str
    edited_latex: str
    model_name: str
    model_version: str
    status: str = STATUS_NORMAL
    has_original: bool = False
    original_ext: str = ""
    error: str = ""
    image_path: str = field(default="", repr=False)
    dir_path: str = field(default="", repr=False)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _atomic_write(path: str, data: bytes) -> None:
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class HistoryStore:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or config.history_dir()
        os.makedirs(self.base_dir, exist_ok=True)

    def _record_dir(self, record_id: str) -> str:
        safe = "".join(c for c in record_id if c.isalnum() or c in "-_")
        return os.path.join(self.base_dir, safe)

    def create_record(
        self,
        input_method: str,
        image: QImage,
        raw_latex: str,
        model_name: str,
        model_version: str,
        original_path: str | None = None,
    ) -> HistoryRecord:
        record_id = uuid.uuid4().hex
        now = _now()
        rec = HistoryRecord(
            record_id=record_id,
            created_at=now,
            updated_at=now,
            input_method=input_method,
            raw_latex=raw_latex,
            edited_latex=raw_latex,
            model_name=model_name,
            model_version=model_version,
        )
        rec.dir_path = self._record_dir(record_id)
        os.makedirs(rec.dir_path, exist_ok=True)
        rec.image_path = os.path.join(rec.dir_path, config.INPUT_IMAGE_NAME)
        if not image.save(rec.image_path, "PNG"):
            raise OSError("save input image failed")
        if original_path:
            ext = os.path.splitext(original_path)[1].lstrip(".").lower() or "bin"
            dst = os.path.join(rec.dir_path, f"{config.ORIGINAL_FILE_NAME}.{ext}")
            shutil.copyfile(original_path, dst)
            rec.has_original = True
            rec.original_ext = ext
        self._write_meta(rec)
        return rec

    def _write_meta(self, rec: HistoryRecord) -> None:
        meta = {
            "record_id": rec.record_id,
            "created_at": rec.created_at,
            "updated_at": rec.updated_at,
            "input_method": rec.input_method,
            "raw_latex": rec.raw_latex,
            "edited_latex": rec.edited_latex,
            "model_name": rec.model_name,
            "model_version": rec.model_version,
            "status": rec.status,
            "has_original": rec.has_original,
            "original_ext": rec.original_ext,
        }
        path = os.path.join(rec.dir_path, config.META_FILE_NAME)
        _atomic_write(
            path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")
        )

    def update_source(self, rec: HistoryRecord, latex: str) -> bool:
        rec.edited_latex = latex
        rec.updated_at = _now()
        try:
            self._write_meta(rec)
            if rec.status == STATUS_SAVE_FAILED:
                rec.status = STATUS_NORMAL
                self._write_meta(rec)
            return True
        except OSError:
            rec.status = STATUS_SAVE_FAILED
            return False

    def list_records(self) -> list[HistoryRecord]:
        records: list[HistoryRecord] = []
        if not os.path.isdir(self.base_dir):
            return records
        for name in sorted(os.listdir(self.base_dir)):
            dir_path = os.path.join(self.base_dir, name)
            if not os.path.isdir(dir_path):
                continue
            meta_path = os.path.join(dir_path, config.META_FILE_NAME)
            image_path = os.path.join(dir_path, config.INPUT_IMAGE_NAME)
            try:
                with open(meta_path, "rb") as f:
                    meta = json.loads(f.read().decode("utf-8"))
                rec = HistoryRecord(
                    record_id=str(meta.get("record_id", name)),
                    created_at=str(meta.get("created_at", "")),
                    updated_at=str(meta.get("updated_at", "")),
                    input_method=str(meta.get("input_method", "")),
                    raw_latex=str(meta.get("raw_latex", "")),
                    edited_latex=str(meta.get("edited_latex", "")),
                    model_name=str(meta.get("model_name", "")),
                    model_version=str(meta.get("model_version", "")),
                    status=str(meta.get("status", STATUS_NORMAL)),
                    has_original=bool(meta.get("has_original", False)),
                    original_ext=str(meta.get("original_ext", "")),
                )
            except (OSError, ValueError, KeyError) as exc:
                rec = HistoryRecord(
                    record_id=name,
                    created_at="",
                    updated_at="",
                    input_method="",
                    raw_latex="",
                    edited_latex="",
                    model_name="",
                    model_version="",
                    status=STATUS_READ_ERROR,
                    error=str(exc),
                )
            rec.dir_path = dir_path
            rec.image_path = image_path if os.path.exists(image_path) else ""
            records.append(rec)
        records.sort(key=lambda r: r.updated_at, reverse=True)
        return records

    def delete_record(self, rec: HistoryRecord) -> bool:
        try:
            shutil.rmtree(rec.dir_path)
            return True
        except OSError:
            return False

    def total_size_bytes(self) -> int:
        total = 0
        for root, _dirs, files in os.walk(self.base_dir):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    continue
        return total

    def disk_free_bytes(self) -> int:
        usage = shutil.disk_usage(self.base_dir)
        return usage.free
