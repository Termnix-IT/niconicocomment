from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
)

from settings import AppSettings


class SettingsDialog(QDialog):
    settings_applied = pyqtSignal(object)

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(360)
        self._settings = settings.normalized()

        layout = QVBoxLayout(self)
        layout.addWidget(self._create_comment_group())
        layout.addWidget(self._create_display_group())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)

    def _create_comment_group(self) -> QGroupBox:
        group = QGroupBox("コメント生成")
        form = QFormLayout(group)

        self.comment_count = QSpinBox()
        self.comment_count.setRange(1, 20)
        self.comment_count.setSuffix(" 件")
        self.comment_count.setValue(self._settings.comment_count)
        form.addRow("1回あたりの表示数", self.comment_count)

        self.capture_interval = QSpinBox()
        self.capture_interval.setRange(1, 60)
        self.capture_interval.setSuffix(" 秒")
        self.capture_interval.setValue(self._settings.capture_interval_ms // 1000)
        form.addRow("分析間隔", self.capture_interval)

        self.spawn_delay = QSpinBox()
        self.spawn_delay.setRange(0, 3000)
        self.spawn_delay.setSingleStep(100)
        self.spawn_delay.setSuffix(" ms")
        self.spawn_delay.setValue(self._settings.comment_spawn_delay_ms)
        form.addRow("流し始めの間隔", self.spawn_delay)

        return group

    def _create_display_group(self) -> QGroupBox:
        group = QGroupBox("表示")
        form = QFormLayout(group)

        self.lane_count = QSpinBox()
        self.lane_count.setRange(1, 30)
        self.lane_count.setSuffix(" レーン")
        self.lane_count.setValue(self._settings.lane_count)
        form.addRow("レーン数", self.lane_count)

        font_row = QHBoxLayout()
        self.font_size_min = QSpinBox()
        self.font_size_min.setRange(10, 96)
        self.font_size_min.setSuffix(" px")
        self.font_size_min.setValue(self._settings.font_size_min)
        self.font_size_max = QSpinBox()
        self.font_size_max.setRange(10, 96)
        self.font_size_max.setSuffix(" px")
        self.font_size_max.setValue(self._settings.font_size_max)
        font_row.addWidget(self.font_size_min)
        font_row.addWidget(self.font_size_max)
        form.addRow("文字サイズ 最小 / 最大", font_row)

        speed_row = QHBoxLayout()
        self.speed_min = QDoubleSpinBox()
        self.speed_min.setRange(0.5, 30.0)
        self.speed_min.setSingleStep(0.5)
        self.speed_min.setSuffix(" px/tick")
        self.speed_min.setValue(self._settings.comment_speed_min)
        self.speed_max = QDoubleSpinBox()
        self.speed_max.setRange(0.5, 30.0)
        self.speed_max.setSingleStep(0.5)
        self.speed_max.setSuffix(" px/tick")
        self.speed_max.setValue(self._settings.comment_speed_max)
        speed_row.addWidget(self.speed_min)
        speed_row.addWidget(self.speed_max)
        form.addRow("速度 最小 / 最大", speed_row)

        return group

    def current_settings(self) -> AppSettings:
        return AppSettings(
            comment_count=self.comment_count.value(),
            capture_interval_ms=self.capture_interval.value() * 1000,
            comment_spawn_delay_ms=self.spawn_delay.value(),
            lane_count=self.lane_count.value(),
            font_size_min=self.font_size_min.value(),
            font_size_max=self.font_size_max.value(),
            comment_speed_min=self.speed_min.value(),
            comment_speed_max=self.speed_max.value(),
        ).normalized()

    def _on_apply(self) -> None:
        self._settings = self.current_settings()
        self._settings.save()
        self.settings_applied.emit(self._settings)
