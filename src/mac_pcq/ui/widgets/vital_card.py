"""VitalCard：心率 / 呼吸率大字卡片（参见 UI 设计 §6.1.4）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from mac_pcq.ui import theme


class VitalCard(QWidget):
    """显示 HR / RR / 电量 / 运行时长。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.current()
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(4)

        # HR 行
        hr_row = QHBoxLayout()
        self._hr_lbl = QLabel("HR  心率")
        self._hr_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        self._hr_val = QLabel("--")
        self._hr_val.setStyleSheet(
            f"color:{L['accent_danger']};font-family:Roboto Mono,monospace;"
            f"font-size:28px;font-weight:700;"
        )
        self._hr_unit = QLabel("bpm")
        self._hr_unit.setStyleSheet(f"color:{L['text_tertiary']};font-size:12px;")
        self._hr_q = QLabel("--")
        self._hr_q.setStyleSheet(f"color:{L['accent_success']};font-size:12px;")
        hr_row.addWidget(self._hr_lbl)
        hr_row.addStretch(1)
        hr_row.addWidget(self._hr_val)
        hr_row.addWidget(self._hr_unit)
        hr_row.addSpacing(8)
        hr_row.addWidget(self._hr_q)
        root.addLayout(hr_row)

        # RR 行
        rr_row = QHBoxLayout()
        self._rr_lbl = QLabel("RR  呼吸率")
        self._rr_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        self._rr_val = QLabel("--")
        self._rr_val.setStyleSheet(
            f"color:{L['accent_info']};font-family:Roboto Mono,monospace;"
            f"font-size:28px;font-weight:700;"
        )
        self._rr_unit = QLabel("bpm")
        self._rr_unit.setStyleSheet(f"color:{L['text_tertiary']};font-size:12px;")
        rr_row.addWidget(self._rr_lbl)
        rr_row.addStretch(1)
        rr_row.addWidget(self._rr_val)
        rr_row.addWidget(self._rr_unit)
        root.addLayout(rr_row)

        # 底部状态
        bot = QHBoxLayout()
        self._bat_lbl = QLabel("电量: --%")
        self._bat_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        self._uptime_lbl = QLabel("运行时长: 00:00:00")
        self._uptime_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        bot.addWidget(self._bat_lbl)
        bot.addStretch(1)
        bot.addWidget(self._uptime_lbl)
        root.addLayout(bot)

        self._apply_theme()

    def _apply_theme(self) -> None:
        L = theme.current()
        self.setStyleSheet(
            f"background:{L['bg_secondary']};border:1px solid {L['border_default']};"
            f"border-radius:8px;"
        )

    def restyle(self) -> None:
        """主题切换时调用。"""
        self._apply_theme()
        # 子 label 重设
        L = theme.current()
        self._hr_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        self._hr_val.setStyleSheet(
            f"color:{L['accent_danger']};font-family:Roboto Mono,monospace;"
            f"font-size:28px;font-weight:700;"
        )
        self._hr_unit.setStyleSheet(f"color:{L['text_tertiary']};font-size:12px;")
        self._hr_q.setStyleSheet(f"color:{L['accent_success']};font-size:12px;")
        self._rr_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        self._rr_val.setStyleSheet(
            f"color:{L['accent_info']};font-family:Roboto Mono,monospace;"
            f"font-size:28px;font-weight:700;"
        )
        self._rr_unit.setStyleSheet(f"color:{L['text_tertiary']};font-size:12px;")
        self._bat_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        self._uptime_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")

    def update_vital(self, hr_bpm: int, rr_bpm: int, quality: int) -> None:
        self._hr_val.setText(str(hr_bpm))
        self._rr_val.setText(str(rr_bpm))
        self._hr_q.setText(f"● {self._quality_label(quality)}")

    def update_status(self, level_pct: int, uptime_s: int) -> None:
        self._bat_lbl.setText(f"电量: {level_pct}%")
        h = uptime_s // 3600
        m = (uptime_s % 3600) // 60
        s = uptime_s % 60
        self._uptime_lbl.setText(f"运行时长: {h:02d}:{m:02d}:{s:02d}")

    @staticmethod
    def _quality_label(q: int) -> str:
        if q >= 90:
            return "良好"
        if q >= 60:
            return "一般"
        return "差"
