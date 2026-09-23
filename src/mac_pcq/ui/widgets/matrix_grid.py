"""MatrixGrid：4×4 压阻热力图（参见 UI 设计 §6.2 / §8）。

- 单元 60×60px，间距 2px
- 6 种基色 + 5 档深度（通过线性插值近似）
- 数值右下角小字 / 悬停 tooltip
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from mac_pcq.ui import theme


def _interpolate(c1: str, c2: str, t: float) -> QColor:
    a = QColor(c1)
    b = QColor(c2)
    r = int(a.red() * (1 - t) + b.red() * t)
    g = int(a.green() * (1 - t) + b.green() * t)
    bl = int(a.blue() * (1 - t) + b.blue() * t)
    return QColor(r, g, bl)


def _value_to_color(value: float, vmin: float, vmax: float, base: str) -> QColor:
    if vmax <= vmin:
        t = 0.5
    else:
        t = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    stops = theme.COLOR_BASES.get(base, theme.COLOR_BASES["blue_red"])
    pos = t * (len(stops) - 1)
    idx = int(pos)
    frac = pos - idx
    if idx >= len(stops) - 1:
        return QColor(stops[-1])
    return _interpolate(stops[idx], stops[idx + 1], frac)


class MatrixGrid(QWidget):
    """4×4 矩阵热力图。"""

    def __init__(
        self,
        cell: int = 60,
        gap: int = 2,
        base: str = "blue_red",
        vmin: float = 10.0,
        vmax: float = 500.0,
        unit: str = "kΩ",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cell = cell
        self.gap = gap
        self.base = base
        self.vmin = vmin
        self.vmax = vmax
        self.unit = unit
        self._values: List[float] = [0.0] * 16
        self._hover_idx: Optional[int] = None
        self.setFixedSize(4 * cell + 3 * gap, 4 * cell + 3 * gap)
        self.setMouseTracking(True)

    def set_values(self, values_16: List[float]) -> None:
        if len(values_16) != 16:
            return
        self._values = list(values_16)
        self.update()

    def set_range(self, vmin: float, vmax: float) -> None:
        self.vmin = vmin
        self.vmax = vmax
        self.update()

    def set_base(self, base: str) -> None:
        self.base = base
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        L = theme.current()
        for i in range(16):
            row, col = i // 4, i % 4
            x = col * (self.cell + self.gap)
            y = row * (self.cell + self.gap)
            color = _value_to_color(self._values[i], self.vmin, self.vmax, self.base)
            p.setBrush(QBrush(color))
            pen_color = QColor(L["brand_primary"]) if self._hover_idx == i else QColor(L["border_default"])
            pen_w = 2 if self._hover_idx == i else 1
            p.setPen(QPen(pen_color, pen_w))
            p.drawRect(x, y, self.cell, self.cell)
            # 右下角数值
            p.setPen(QColor(L["text_primary"]))
            f = QFont()
            f.setPixelSize(10)
            p.setFont(f)
            txt = f"{self._values[i]:.1f}"
            text_rect = QRectF(x + self.cell - 36, y + self.cell - 16, 32, 14)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, txt)
        p.end()

    def restyle(self) -> None:
        self.update()

    def mouseMoveEvent(self, evt) -> None:
        pos = evt.position() if hasattr(evt, "position") else QPointF(evt.pos())
        x, y = int(pos.x()), int(pos.y())
        col = x // (self.cell + self.gap)
        row = y // (self.cell + self.gap)
        if 0 <= row < 4 and 0 <= col < 4:
            self._hover_idx = row * 4 + col
            self.setToolTip(f"ch{self._hover_idx + 1}: {self._values[self._hover_idx]:.2f} {self.unit}")
            self.update()
        else:
            self._hover_idx = None
            self.setToolTip("")
            self.update()

    def leaveEvent(self, _evt) -> None:
        self._hover_idx = None
        self.setToolTip("")
        self.update()
