from __future__ import annotations

import csv
import threading
import time
from datetime import datetime
from pathlib import Path

from config import PERF_LOG_ENABLED, PERF_LOG_PATH

_lock = threading.Lock()
_path: Path | None = Path(__file__).with_name(PERF_LOG_PATH) if PERF_LOG_ENABLED else None
_header_written = False


def _ensure_header() -> None:
    global _header_written
    if _header_written or _path is None:
        return
    if not _path.exists():
        with _path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "event", "duration_ms", "extra"])
    _header_written = True


def record(event: str, duration_ms: float, extra: str = "") -> None:
    """Append one measurement row to the CSV log. No-op if disabled."""
    if _path is None:
        return
    with _lock:
        _ensure_header()
        with _path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now().isoformat(timespec="milliseconds"),
                event,
                f"{duration_ms:.2f}",
                extra,
            ])


class measure:
    """Context manager that records elapsed wall time on exit.

    Usage:
        with perf_log.measure("capture", extra="skipped"):
            ...
    """

    __slots__ = ("event", "extra", "_start")

    def __init__(self, event: str, extra: str = "") -> None:
        self.event = event
        self.extra = extra

    def __enter__(self) -> "measure":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_exc) -> None:
        record(self.event, (time.perf_counter() - self._start) * 1000.0, self.extra)

    def set_extra(self, extra: str) -> None:
        self.extra = extra
