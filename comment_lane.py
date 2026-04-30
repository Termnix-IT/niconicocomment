from __future__ import annotations
import random
from dataclasses import dataclass
from PyQt6.QtGui import QColor, QFont, QPainterPath
from config import (
    LANE_PADDING, FONT_FAMILY, FONT_BOLD, COMMENT_COLORS,
)
from settings import AppSettings


@dataclass
class Comment:
    text: str
    lane: int        # 0-based row index
    x: float         # current left-edge x (float for sub-pixel motion)
    speed: float     # pixels per animation tick
    color: QColor
    font: QFont
    text_width: int  # pre-measured pixel width
    text_path: QPainterPath | None = None
    baseline: int = 0
    alive: bool = True

    def advance(self) -> None:
        self.x -= self.speed
        if self.x + self.text_width < 0:
            self.alive = False


class CommentLaneManager:
    """Manages lane assignment and per-tick position updates."""

    _MIN_GAP = 80  # px gap required before a new comment enters the same lane

    def __init__(
        self,
        overlay_width: int,
        overlay_height: int,
        settings: AppSettings | None = None,
    ) -> None:
        self.overlay_width  = overlay_width
        self.overlay_height = overlay_height
        self._settings = (settings or AppSettings()).normalized()
        self._comments: list[Comment] = []
        # Tracks rightmost x of the latest comment per lane
        self._lane_tail_x: list[float] = [float("-inf")] * self._settings.lane_count

    def update_settings(self, settings: AppSettings) -> None:
        self._settings = settings.normalized()
        self._comments = [
            c for c in self._comments
            if c.lane < self._settings.lane_count
        ]
        self._recompute_lane_tails()

    def resize(self, width: int, height: int) -> None:
        self.overlay_width  = width
        self.overlay_height = height

    def lane_y(self, lane: int) -> int:
        """Top-of-text y for a given lane index."""
        usable = self.overlay_height - LANE_PADDING * 2
        lane_h = max(1, usable // self._settings.lane_count)
        return LANE_PADDING + lane * lane_h

    def _pick_lane(self) -> int:
        """Pick a lane with enough free space; fall back to least-crowded."""
        free = [
            i for i in range(self._settings.lane_count)
            if self._lane_tail_x[i] < self.overlay_width - self._MIN_GAP
        ]
        if free:
            return random.choice(free)
        return min(range(self._settings.lane_count), key=lambda i: self._lane_tail_x[i])

    def spawn_comment(self, text: str, measure_fn) -> Comment:
        """Create a Comment and add it to the manager.

        measure_fn(font, text) -> int  — provided by OverlayWindow to avoid
        importing QApplication here.
        """
        font = QFont(
            FONT_FAMILY,
            random.randint(self._settings.font_size_min, self._settings.font_size_max),
        )
        font.setBold(FONT_BOLD)
        text_width = measure_fn(font, text)
        lane  = self._pick_lane()
        color = QColor(*random.choice(COMMENT_COLORS))
        speed = random.uniform(
            self._settings.comment_speed_min,
            self._settings.comment_speed_max,
        )

        comment = Comment(
            text=text,
            lane=lane,
            x=float(self.overlay_width),
            speed=speed,
            color=color,
            font=font,
            text_width=text_width,
        )
        self._comments.append(comment)
        self._lane_tail_x[lane] = float(self.overlay_width) + text_width
        return comment

    def tick(self) -> None:
        """Advance all live comments, purge dead ones, and recompute lane tails."""
        for c in self._comments:
            c.advance()
        self._comments = [c for c in self._comments if c.alive]
        # Recompute from live comments so lanes are freed after comments scroll off
        self._recompute_lane_tails()

    def _recompute_lane_tails(self) -> None:
        self._lane_tail_x = [float("-inf")] * self._settings.lane_count
        for c in self._comments:
            if c.lane >= self._settings.lane_count:
                continue
            tail = c.x + c.text_width
            if tail > self._lane_tail_x[c.lane]:
                self._lane_tail_x[c.lane] = tail

    @property
    def active_comments(self) -> list[Comment]:
        return self._comments
