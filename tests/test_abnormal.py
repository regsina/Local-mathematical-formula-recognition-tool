import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from src.history_store import HistoryStore
from src.recognizer.placeholder import PlaceholderRecognizer
from src.task_manager import STATE_IDLE

app = QApplication.instance() or QApplication([])

from PySide6.QtWidgets import QMessageBox

QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

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
    print(("PASS" if cond else "FAIL"), name, flush=True)
    if not cond:
        failures.append(name)


def make_image():
    img = QImage(64, 32, QImage.Format.Format_RGB888)
    img.fill(QColor(255, 255, 255))
    return img


def test_cancel_then_retry_no_duplicate_history():
    base = tempfile.mkdtemp(prefix="lfr_g2_")
    try:
        from src.main_window import MainWindow

        store = HistoryStore(base)
        window = MainWindow(store=store, recognizer=PlaceholderRecognizer(delay_s=1.0))
        window._set_input_image(make_image(), "截图", None, window._shot_preview)

        window._submit("截图")
        window._task_manager.cancel()
        wait_until(lambda: window._task_manager.state == STATE_IDLE)
        window._submit("截图")
        wait_until(lambda: window._current_record is not None, timeout_ms=15000)
        records = store.list_records()
        check("cancel then retry: exactly one record", len(records) == 1)
        window.deleteLater()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_empty_source_cannot_copy():
    base = tempfile.mkdtemp(prefix="lfr_g2_")
    try:
        from src.main_window import MainWindow

        window = MainWindow(
            store=HistoryStore(base), recognizer=PlaceholderRecognizer(0.1)
        )
        window._editor_preview.editor.setPlainText("")
        window._copy_source()
        check("empty source copy rejected", "源码为空" in window._status_label.text())
        window.deleteLater()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_blank_canvas_rejected():
    base = tempfile.mkdtemp(prefix="lfr_g2_")
    try:
        from src.main_window import MainWindow

        window = MainWindow(
            store=HistoryStore(base), recognizer=PlaceholderRecognizer(0.1)
        )
        window._canvas.clear()
        check("canvas blank check", window._canvas.is_blank())
        window._submit("鼠标手写")
        check("blank canvas submit rejected", "画板为空" in window._status_label.text())
        check("no task started for blank canvas", not window._task_manager.is_busy())
        window.deleteLater()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_history_delete_removes_files():
    base = tempfile.mkdtemp(prefix="lfr_g2_")
    try:
        store = HistoryStore(base)
        rec = store.create_record("截图", make_image(), r"x^2", "placeholder", "0.0.0")
        rec_dir = rec.dir_path
        check("record dir exists before delete", os.path.isdir(rec_dir))
        ok = store.delete_record(rec)
        check("delete returns true", ok)
        check("record dir removed after delete", not os.path.isdir(rec_dir))
        check("list empty after delete", store.list_records() == [])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_undecodable_image_rejected():
    base = tempfile.mkdtemp(prefix="lfr_g2_")
    try:
        from src.main_window import MainWindow

        bad = os.path.join(base, "broken.png")
        with open(bad, "wb") as f:
            f.write(b"this is not a png file at all")
        window = MainWindow(
            store=HistoryStore(base), recognizer=PlaceholderRecognizer(0.1)
        )
        window._load_image_file(bad)
        check("undecodable image: no input loaded", window._current_image is None)
        window.deleteLater()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_canvas_undo_and_clear():
    from PySide6.QtCore import QPointF

    from src.input_canvas import CanvasWidget

    canvas = CanvasWidget()
    stroke = {"eraser": False, "points": [QPointF(1, 1), QPointF(2, 2)]}
    canvas._strokes = [stroke]
    check("canvas not blank with stroke", not canvas.is_blank())
    canvas.undo()
    check("undo removes stroke, blank again", canvas.is_blank())
    canvas._strokes = [stroke]
    canvas.clear()
    check("clear resets canvas", canvas.is_blank())
    img = canvas.export_image()
    check("export image size fixed", img.width() == 960 and img.height() == 540)


def test_screenshot_cancel_no_record():
    base = tempfile.mkdtemp(prefix="lfr_g2_")
    try:
        store = HistoryStore(base)
        window = None
        from src.main_window import MainWindow

        window = MainWindow(store=store, recognizer=PlaceholderRecognizer(0.1))
        window._on_screenshot_cancelled()
        check("screenshot cancel: no record created", store.list_records() == [])
        check("screenshot cancel: status set", "已取消" in window._status_label.text())
        window.deleteLater()
    finally:
        shutil.rmtree(base, ignore_errors=True)


test_empty_source_cannot_copy()
test_blank_canvas_rejected()
test_history_delete_removes_files()
test_undecodable_image_rejected()
test_canvas_undo_and_clear()
test_screenshot_cancel_no_record()
test_cancel_then_retry_no_duplicate_history()

print()
if failures:
    print(f"G2 ABNORMAL FAILED: {len(failures)} case(s): {failures}")
    sys.exit(1)
print("G2 ABNORMAL OK")
sys.exit(0)
