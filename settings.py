from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from config import (
    CAPTURE_INTERVAL_MS,
    COMMENT_SPEED_MAX,
    COMMENT_SPEED_MIN,
    COMMENT_SPAWN_DELAY,
    FONT_SIZE_MAX,
    FONT_SIZE_MIN,
    LANE_COUNT,
)


SETTINGS_PATH = Path(__file__).with_name("settings.json")


@dataclass(frozen=True)
class AppSettings:
    comment_count: int = 5
    capture_interval_ms: int = CAPTURE_INTERVAL_MS
    comment_spawn_delay_ms: int = COMMENT_SPAWN_DELAY
    lane_count: int = LANE_COUNT
    font_size_min: int = FONT_SIZE_MIN
    font_size_max: int = FONT_SIZE_MAX
    comment_speed_min: float = float(COMMENT_SPEED_MIN)
    comment_speed_max: float = float(COMMENT_SPEED_MAX)

    @classmethod
    def load(cls) -> "AppSettings":
        if not SETTINGS_PATH.exists():
            return cls()
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()

        allowed = {field.name for field in fields(cls)}
        values = {key: value for key, value in raw.items() if key in allowed}
        return cls(**values).normalized()

    def save(self) -> None:
        SETTINGS_PATH.write_text(
            json.dumps(asdict(self.normalized()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def normalized(self) -> "AppSettings":
        values: dict[str, Any] = asdict(self)
        values["comment_count"] = _clamp_int(values["comment_count"], 1, 20)
        values["capture_interval_ms"] = _clamp_int(values["capture_interval_ms"], 1_000, 60_000)
        values["comment_spawn_delay_ms"] = _clamp_int(values["comment_spawn_delay_ms"], 0, 3_000)
        values["lane_count"] = _clamp_int(values["lane_count"], 1, 30)
        values["font_size_min"] = _clamp_int(values["font_size_min"], 10, 96)
        values["font_size_max"] = _clamp_int(values["font_size_max"], 10, 96)
        values["comment_speed_min"] = _clamp_float(values["comment_speed_min"], 0.5, 30.0)
        values["comment_speed_max"] = _clamp_float(values["comment_speed_max"], 0.5, 30.0)

        if values["font_size_min"] > values["font_size_max"]:
            values["font_size_min"], values["font_size_max"] = (
                values["font_size_max"],
                values["font_size_min"],
            )
        if values["comment_speed_min"] > values["comment_speed_max"]:
            values["comment_speed_min"], values["comment_speed_max"] = (
                values["comment_speed_max"],
                values["comment_speed_min"],
            )
        return AppSettings(**values)


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return minimum


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        return max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return minimum
