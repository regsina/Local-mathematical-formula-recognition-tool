import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from src.history_store import STATUS_READ_ERROR, HistoryStore
from src.recognizer.placeholder import PlaceholderRecognizer
from src.renderer import render_latex
from src.task_manager import (
    STATE_CANCELLING,
    STATE_IDLE,
    STATE_RECOGNIZING,
    TaskManager,
)

from src import config

app = QApplication.instance() or QApplication([])

failures = []


def wait_until(pred, timeout_ms: int = 8000) -> bool:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(50)
    timer.timeout.connect(lambda: pred() and loop.quit())
    QTimer.singleShot(timeout_ms, loop.quit)
    timer.start()
    loop.exec()
    timer.stop()
    return pred()


def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        failures.append(name)


def make_image():
    img = QImage(64, 32, QImage.Format.Format_RGB888)
    img.fill(QColor(255, 255, 255))
    return img


def test_history_store():
    base = tempfile.mkdtemp(prefix="lfr_hist_")
    try:
        store = HistoryStore(base)
        rec = store.create_record(
            "截图", make_image(), r"x^2+y^2=r^2", "placeholder", "0.0.0"
        )
        check("create_record fields", rec.record_id and rec.raw_latex == r"x^2+y^2=r^2")
        check("create_record image saved", os.path.exists(rec.image_path))
        records = store.list_records()
        check("list_records count", len(records) == 1)
        ok = store.update_source(rec, r"a_n")
        check("update_source ok", ok and rec.edited_latex == r"a_n")
        records = store.list_records()
        check("list_records updated", records[0].edited_latex == r"a_n")
        with open(os.path.join(rec.dir_path, config.META_FILE_NAME), "wb") as f:
            f.write(b"{broken json")
        records = store.list_records()
        check(
            "broken record isolated",
            len(records) == 1 and records[0].status == STATUS_READ_ERROR,
        )
        check(
            "delete_record",
            store.delete_record(records[0]) and store.list_records() == [],
        )
        check("total_size_bytes >= 0", store.total_size_bytes() >= 0)
        check("disk_free_bytes > 0", store.disk_free_bytes() > 0)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_renderer():
    r1 = render_latex(r"x^2+\frac{a}{b}")
    check("render ok", r1.ok)
    r2 = render_latex(r"\frac{a}{")
    check("render invalid fails with message", not r2.ok and bool(r2.error))
    r3 = render_latex("x" * (config.MAX_SOURCE_CHARS + 1))
    check("render oversize rejected", not r3.ok)
    r4 = render_latex("   ")
    check("render blank rejected", not r4.ok)


def test_task_manager():
    tm = TaskManager(PlaceholderRecognizer(delay_s=0.3))
    results = {}
    tm.recognizeSucceeded.connect(
        lambda tid, latex, mn, mv: results.update(ok=True, latex=latex)
    )
    tm.recognizeFailed.connect(
        lambda tid, reason: results.update(ok=False, reason=reason)
    )
    task_id = tm.start(make_image())
    check("task id assigned", task_id > 0)
    check("state recognizing", tm.state == STATE_RECOGNIZING)
    wait_until(lambda: "ok" in results)
    check("recognize succeeded", results.get("ok") is True)
    check("state idle after success", tm.state == STATE_IDLE)
    check("latex is placeholder demo", "RAG-Sequence" in results.get("latex", ""))

    results.clear()
    cancelled = {"done": False}
    tm.cancelFinished.connect(lambda: cancelled.update(done=True))
    tm.start(make_image())
    tm.cancel()
    check("state cancelling", tm.state == STATE_CANCELLING)
    wait_until(lambda: cancelled["done"] or tm.state == STATE_IDLE)
    check("cancel finished", cancelled["done"])
    check("state idle after cancel", tm.state == STATE_IDLE)
    check("no success emitted after cancel", not results.get("ok"))


def test_main_window():
    from src.main_window import MainWindow

    base = tempfile.mkdtemp(prefix="lfr_win_")
    try:
        store = HistoryStore(base)
        window = MainWindow(store=store)
        check("main window created", window is not None)
        window._set_input_image(make_image(), "截图", None, window._shot_preview)
        window._submit("截图")
        wait_until(lambda: window._current_record is not None)
        text = window._editor_preview.editor.toPlainText()
        check("editor filled after recognize", "RAG-Sequence" in text)
        check("record created", window._current_record is not None)
        records = store.list_records()
        check("store persisted record", len(records) == 1)
        window._editor_preview.editor.setPlainText(r"a+b=c")
        wait_until(lambda: store.list_records()[0].edited_latex == r"a+b=c")
        records = store.list_records()
        check("autosave updated record", records[0].edited_latex == r"a+b=c")
        window.deleteLater()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_env_check():
    from src.env_check import run_all_checks

    items = run_all_checks()
    names = [i.name for i in items]
    check("env check items", "操作系统" in names and "磁盘空间" in names)


test_history_store()
test_renderer()
test_task_manager()
test_main_window()
test_env_check()

print()
if failures:
    print(f"SMOKE FAILED: {len(failures)} case(s): {failures}")
    sys.exit(1)
print("SMOKE OK")
sys.exit(0)
