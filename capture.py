from __future__ import annotations
import base64
import time
import zlib
from dataclasses import dataclass
from io import BytesIO

import mss
import win32gui
from PIL import Image

import perf_log
from config import CAPTURE_MAX_DIMENSION


@dataclass
class WindowRect:
    left: int
    top: int
    width: int
    height: int

    @property
    def as_monitor_dict(self) -> dict:
        return {"left": self.left, "top": self.top,
                "width": self.width, "height": self.height}


class ScreenCapture:
    """Captures the screen region of a Win32 window handle.

    Uses mss for pixel grab and mss.tools.to_png for encoding.
    No PIL dependency.
    """

    def __init__(self, hwnd: int) -> None:
        self.hwnd = hwnd
        self._sct = mss.mss()

    def get_window_rect(self) -> WindowRect | None:
        try:
            if not win32gui.IsWindow(self.hwnd):
                return None
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            w, h = right - left, bottom - top
            if w <= 0 or h <= 0:
                return None
            return WindowRect(left=left, top=top, width=w, height=h)
        except Exception:
            return None

    def capture_base64_png(self) -> tuple[str, int] | None:
        """Returns base64-encoded PNG and a frame signature, or None on failure."""
        rect = self.get_window_rect()
        if rect is None:
            return None
        t0 = time.perf_counter()
        try:
            img = self._sct.grab(rect.as_monitor_dict)
            t_grab = time.perf_counter()
            # Frame signature on the original (raw) frame so dedup behavior is independent of resize
            frame_signature = zlib.crc32(img.rgb)

            pil_img = Image.frombytes("RGB", img.size, img.rgb)
            longest = max(pil_img.size)
            if longest > CAPTURE_MAX_DIMENSION:
                scale = CAPTURE_MAX_DIMENSION / longest
                new_size = (max(1, int(pil_img.size[0] * scale)),
                            max(1, int(pil_img.size[1] * scale)))
                pil_img = pil_img.resize(new_size, Image.Resampling.BILINEAR)
            t_resize = time.perf_counter()

            buf = BytesIO()
            pil_img.save(buf, format="PNG", compress_level=1)
            png_bytes = buf.getvalue()
            t_encode = time.perf_counter()

            png_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            t_end = time.perf_counter()
            perf_log.record(
                "capture",
                (t_end - t0) * 1000.0,
                extra=(
                    f"src={rect.width}x{rect.height};"
                    f"sent={pil_img.size[0]}x{pil_img.size[1]};"
                    f"png_bytes={len(png_bytes)};"
                    f"grab_ms={(t_grab - t0) * 1000:.2f};"
                    f"resize_ms={(t_resize - t_grab) * 1000:.2f};"
                    f"encode_ms={(t_encode - t_resize) * 1000:.2f};"
                    f"b64_ms={(t_end - t_encode) * 1000:.2f}"
                ),
            )
            return png_b64, frame_signature
        except Exception as exc:
            print(f"[capture] Error: {exc}")
            return None

    def close(self) -> None:
        self._sct.close()
