"""StatusBadge：状态徽章（采集/暂停/错误）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget

from ...domain.session import SessionState
from mac_pcq.ui import theme


class StatusBadge(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state = SessionState.IDLE
        self.setFixedHeight(22)
        self.setMinimumWidth(64)
        self.setToolTip("会话状态")

    def set_state(self, s: SessionState) -> None:
        self._state = s
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg, fg = self._colors()
        p.setBrush(QBrush(QColor(bg)))
        p.setPen(QPen(QColor(bg).darker(110), 1))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 11, 11)
        p.setPen(QColor(fg))
        f = QFont()
        f.setPixelSize(12)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._label())
        p.end()

    def _colors(self) -> tuple[str, str]:
        L = theme.current()
        return {
            SessionState.IDLE: (L["bg_secondary"], L["text_secondary"]),
            SessionState.STARTING: (L["accent_warning"], "#FFFFFF"),
            SessionState.RUNNING: (L["accent_success"], "#FFFFFF"),
            SessionState.PAUSED: (L["bg_tertiary"], L["text_primary"]),
            SessionState.RECORDING: (L["accent_danger"], "#FFFFFF"),
            SessionState.STOPPING: (L["accent_warning"], "#FFFFFF"),
            SessionState.ERROR: (L["accent_danger"], "#FFFFFF"),
        }.get(self._state, (L["bg_secondary"], L["text_primary"]))

    def restyle(self) -> None:
        self.update()

    def _label(self) -> str:
        return {
            SessionState.IDLE: "空闲",
            SessionState.STARTING: "启动中",
            SessionState.RUNNING: "采集中",
            SessionState.PAUSED: "已暂停",
            SessionState.RECORDING: "录制中",
            SessionState.STOPPING: "停止中",
            SessionState.ERROR: "错误",
        }.get(self._state, str(self._state.value))
