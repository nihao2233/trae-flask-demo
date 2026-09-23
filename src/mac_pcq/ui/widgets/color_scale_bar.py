"""ColorScaleBar：色阶图例（参见 UI 设计 §6.2.3）。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QFont
from PySide6.QtWidgets import QWidget

from .matrix_grid import _interpolate
from mac_pcq.ui import theme


class ColorScaleBar(QWidget):
    def __init__(self, base: str = "blue_red", vmin: float = 0.0, vmax: float = 500.0, unit: str = "kΩ", parent=None) -> None:
        super().__init__(parent)
        self.base = base
        self.vmin = vmin
        self.vmax = vmax
        self.unit = unit
        self.setFixedHeight(24)

    def set_range(self, vmin: float, vmax: float) -> None:
        self.vmin = vmin
        self.vmax = vmax
        self.update()

    def set_base(self, base: str) -> None:
        self.base = base
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        r = QRectF(0, 4, self.width() - 80, 16)
        stops = theme.COLOR_BASES.get(self.base, theme.COLOR_BASES["blue_red"])
        grad = QLinearGradient(r.left(), 0, r.right(), 0)
        n = len(stops)
        for i, c in enumerate(stops):
            grad.setColorAt(i / max(1, n - 1), QColor(c))
        p.fillRect(r, QBrush(grad))
        L = theme.current()
        p.setPen(QColor(L["border_default"]))
        p.drawRect(r)

        f = QFont()
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(QColor(L["text_secondary"]))
        p.drawText(self.width() - 76, 6, f"{self.vmax:.0f} {self.unit}")
        p.drawText(self.width() - 76, 18, f"{self.vmin:.0f} {self.unit}")
        p.end()

    def restyle(self) -> None:
        self.update()
