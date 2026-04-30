from __future__ import annotations
import ctypes
import threading
import time

import win32gui
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor, QFontMetrics
from PyQt6.QtWidgets import QWidget, QMessageBox

from capture import ScreenCapture
from analyzer import CommentAnalyzer
from comment_lane import CommentLaneManager
from config import (
    ANIMATION_TICK_MS, WINDOW_TRACK_INTERVAL_MS, OUTLINE_COLOR, OUTLINE_WIDTH,
)
from settings import AppSettings
import perf_log

_user32 = ctypes.WinDLL("user32", use_last_error=True)


# ---------------------------------------------------------------------------
# Worker: runs in a QThread, never touches Qt widgets
# ---------------------------------------------------------------------------

class AnalyzerWorker(QObject):
    comments_ready = pyqtSignal(list)
    finished       = pyqtSignal()
    error          = pyqtSignal(str)

    def __init__(self, hwnd: int, settings: AppSettings) -> None:
        super().__init__()
        self._hwnd       = hwnd
        self._stop_event = threading.Event()
        self._settings   = settings.normalized()

    def run(self) -> None:
        try:
            analyzer = CommentAnalyzer(self._settings.comment_count)
        except RuntimeError as exc:
            self.error.emit(str(exc))
            self.finished.emit()
            return

        capture = ScreenCapture(self._hwnd)
        last_frame_signature: int | None = None

        try:
            while not self._stop_event.is_set():
                captured = capture.capture_base64_png()
                if captured:
                    png_b64, frame_signature = captured
                    if frame_signature != last_frame_signature:
                        analyzer.set_comment_count(self._settings.comment_count)
                        comments = analyzer.generate_comments(png_b64)
                        if comments:
                            self.comments_ready.emit(comments)
                        last_frame_signature = frame_signature

                # wait() returns True immediately when stop is signalled
                self._stop_event.wait(self._settings.capture_interval_ms / 1000.0)
        finally:
            capture.close()

        self.finished.emit()

    def stop(self) -> None:
        self._stop_event.set()

    @pyqtSlot(object)
    def apply_settings(self, settings: AppSettings) -> None:
        self._settings = settings.normalized()


# ---------------------------------------------------------------------------
# OverlayWindow
# ---------------------------------------------------------------------------

class OverlayWindow(QWidget):
    """Transparent, always-on-top, click-through overlay over a target window."""

    def __init__(self, target_hwnd: int, settings: AppSettings) -> None:
        super().__init__(None)
        self._hwnd             = target_hwnd
        self._settings         = settings.normalized()
        self._lane_manager: CommentLaneManager | None = None
        self._pending: list[tuple[str, float]] = []  # (text, spawn_time_monotonic)

        # Tick perf aggregation: sum/max/count over a 1-second window
        self._tick_count = 0
        self._tick_sum_ms = 0.0
        self._tick_max_ms = 0.0
        self._paint_count = 0
        self._paint_sum_ms = 0.0
        self._paint_max_ms = 0.0

        self._setup_flags()
        self._setup_geometry()
        self._setup_timers()
        self._setup_worker()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _setup_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # hidden from taskbar and Alt+Tab
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _setup_geometry(self) -> None:
        rect = self._target_rect()
        if rect:
            x, y, w, h = rect
            self.setGeometry(x, y, w, h)
            self._lane_manager = CommentLaneManager(w, h, self._settings)
        else:
            self.setGeometry(0, 0, 1280, 720)
            self._lane_manager = CommentLaneManager(1280, 720, self._settings)

    def _setup_timers(self) -> None:
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(ANIMATION_TICK_MS)
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start()

        self._track_timer = QTimer(self)
        self._track_timer.setInterval(WINDOW_TRACK_INTERVAL_MS)
        self._track_timer.timeout.connect(self._sync_geometry)
        self._track_timer.start()

    def _setup_worker(self) -> None:
        self._thread = QThread()
        self._worker = AnalyzerWorker(self._hwnd, self._settings)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.comments_ready.connect(self._on_comments_ready)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    # ------------------------------------------------------------------
    # Win32 click-through — must be called AFTER the window is shown
    # because SetWindowLongW requires a valid HWND
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_click_through()

    def _apply_click_through(self) -> None:
        hwnd = int(self.winId())
        GWL_EXSTYLE       = -20
        WS_EX_LAYERED     = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        current = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        result  = _user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, current | WS_EX_LAYERED | WS_EX_TRANSPARENT
        )
        if result == 0:
            err = ctypes.get_last_error()
            print(f"[overlay] SetWindowLongW failed (error {err}) — overlay may not be click-through")

    # ------------------------------------------------------------------
    # Window tracking
    # ------------------------------------------------------------------

    def _target_rect(self) -> tuple[int, int, int, int] | None:
        try:
            if not win32gui.IsWindow(self._hwnd):
                return None
            l, t, r, b = win32gui.GetWindowRect(self._hwnd)
            w, h = r - l, b - t
            return (l, t, w, h) if w > 0 and h > 0 else None
        except Exception:
            return None

    def _sync_geometry(self) -> None:
        rect = self._target_rect()
        if rect is None:
            self.close()
            return
        x, y, w, h = rect
        if (self.x(), self.y(), self.width(), self.height()) != (x, y, w, h):
            self.setGeometry(x, y, w, h)
            if self._lane_manager:
                self._lane_manager.resize(w, h)

    def apply_settings(self, settings: AppSettings) -> None:
        self._settings = settings.normalized()
        if self._lane_manager:
            self._lane_manager.update_settings(self._settings)
        self._worker.apply_settings(self._settings)

    def settings(self) -> AppSettings:
        return self._settings

    # ------------------------------------------------------------------
    # Comment scheduling (slot: called in main thread via Qt signal)
    # ------------------------------------------------------------------

    def _on_comments_ready(self, comments: list) -> None:
        now = time.monotonic()
        for i, text in enumerate(comments):
            self._pending.append(
                (text, now + i * self._settings.comment_spawn_delay_ms / 1000.0)
            )

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "Ollama エラー", message)
        self.close()

    # ------------------------------------------------------------------
    # Animation tick (~60 fps)
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        if self._lane_manager is None:
            return

        t0 = time.perf_counter()

        now = time.monotonic()
        remaining = []
        for text, scheduled in self._pending:
            if now >= scheduled:
                comment = self._lane_manager.spawn_comment(text, _measure_text)
                comment.baseline = comment.font.pointSize()
                comment.text_path = QPainterPath()
                comment.text_path.addText(0, comment.baseline, comment.font, comment.text)
            else:
                remaining.append((text, scheduled))
        self._pending = remaining

        self._lane_manager.tick()
        self.update()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._tick_count += 1
        self._tick_sum_ms += elapsed_ms
        if elapsed_ms > self._tick_max_ms:
            self._tick_max_ms = elapsed_ms

        # Flush aggregate every ~1 second (60 ticks at 16ms)
        if self._tick_count >= 60:
            avg_ms = self._tick_sum_ms / self._tick_count
            perf_log.record(
                "tick",
                avg_ms,
                extra=(
                    f"samples={self._tick_count};"
                    f"max_ms={self._tick_max_ms:.2f};"
                    f"active_comments={len(self._lane_manager.active_comments)};"
                    f"pending={len(self._pending)}"
                ),
            )
            if self._paint_count > 0:
                paint_avg = self._paint_sum_ms / self._paint_count
                perf_log.record(
                    "paint",
                    paint_avg,
                    extra=(
                        f"samples={self._paint_count};"
                        f"max_ms={self._paint_max_ms:.2f}"
                    ),
                )
            self._tick_count = 0
            self._tick_sum_ms = 0.0
            self._tick_max_ms = 0.0
            self._paint_count = 0
            self._paint_sum_ms = 0.0
            self._paint_max_ms = 0.0

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        if not self._lane_manager:
            return

        t0 = time.perf_counter()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for c in self._lane_manager.active_comments:
            painter.setFont(c.font)
            if c.text_path is None:
                continue

            # Outline (stroke)
            pen = QPen(QColor(*OUTLINE_COLOR), OUTLINE_WIDTH)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.save()
            painter.translate(int(c.x), self._lane_manager.lane_y(c.lane))
            painter.drawPath(c.text_path)

            # Fill
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c.color)
            painter.drawPath(c.text_path)
            painter.restore()

        painter.end()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._paint_count += 1
        self._paint_sum_ms += elapsed_ms
        if elapsed_ms > self._paint_max_ms:
            self._paint_max_ms = elapsed_ms

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._anim_timer.stop()
        self._track_timer.stop()
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(3000)
        super().closeEvent(event)


def _measure_text(font, text: str) -> int:
    return QFontMetrics(font).horizontalAdvance(text)
