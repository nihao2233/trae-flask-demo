"""LinkIndicator：链路状态指示灯（绿/黄/红/灰）。

颜色 Token 见 ui/theme.py LIGHT/DARK。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QBrush, QPen
from PySide6.QtWidgets import QWidget

from ...transport.adapter import LinkState
from mac_pcq.ui import theme


class LinkIndicator(QWidget):
    """圆形指示灯 + tooltip。"""

    _COLORS = {
        LinkState.DISCONNECTED: "text_tertiary",
        LinkState.CONNECTING: "accent_warning",
        LinkState.CONNECTED: "accent_success",
        LinkState.STREAMING: "accent_success",
        LinkState.UPGRADING: "accent_info",
        LinkState.ERROR: "accent_danger",
    }
    _LABELS = {
        LinkState.DISCONNECTED: "未连接",
        LinkState.CONNECTING: "连接中",
        LinkState.CONNECTED: "已连接",
        LinkState.STREAMING: "采集中",
        LinkState.UPGRADING: "升级中",
        LinkState.ERROR: "错误",
    }

    def __init__(self, parent=None, diameter: int = 12) -> None:
        super().__init__(parent)
        self._diameter = diameter
        self._state = LinkState.DISCONNECTED
        self.setFixedSize(diameter + 4, diameter + 4)
        self.setToolTip(self._LABELS[self._state])

    def restyle(self) -> None:
        self.update()

    def set_state(self, s: LinkState) -> None:
        self._state = s
        self.setToolTip(self._LABELS.get(s, str(s)))
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        key = self._COLORS.get(self._state, "text_tertiary")
        color = QColor(theme.current()[key])
        p.setBrush(QBrush(color))
        p.setPen(QPen(color.darker(120), 1))
        r = self._diameter / 2
        p.drawEllipse(2, 2, int(r * 2), int(r * 2))
        p.end()
