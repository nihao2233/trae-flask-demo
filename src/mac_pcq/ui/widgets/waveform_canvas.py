"""WaveformCanvas：通用波形画布（pyqtgraph）。

按 UI 设计 §7：
- pyqtgraph PlotWidget
- 5s 默认滚动窗 / 60fps / 10s 环形缓冲
- 鼠标悬停十字光标
- 滚轮缩放 Y / Shift+滚轮缩放 X
- 双击通道标签重置 Y / 单击显隐
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel

from mac_pcq.ui import theme


class WaveformCanvas(QWidget):
    """多通道波形画布。

    用法：
        wf = WaveformCanvas(channels=4, fs=500, window_s=5.0)
        wf.push_sample((c1, c2, c3, c4))
    """

    def __init__(
        self,
        channels: int = 4,
        fs: int = 500,
        window_s: float = 5.0,
        ring_s: float = 10.0,
        y_range: float = 1.0,
        title: str = "Waveform",
        y_unit: str = "mV",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.channels = channels
        self.fs = fs
        self.window_s = window_s
        self.y_range = y_range
        self._title = title
        self._y_unit = y_unit

        ring_len = int(fs * ring_s)
        self._ring: List[deque] = [deque(maxlen=ring_len) for _ in range(channels)]
        self._t_ring: deque = deque(maxlen=ring_len)
        self._t0 = 0.0
        self._ch_visible: List[bool] = [True] * channels

        pg.setConfigOptions(antialias=True, background="#FFFFFF", foreground="#1F1F1F")
        self.plot = pg.PlotWidget()
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("left", y_unit)
        self.plot.setLabel("bottom", "t", units="s")
        self.plot.setYRange(-y_range, y_range)
        self.plot.setXRange(-window_s, 0)
        self._curves: List[pg.PlotDataItem] = []
        for i in range(channels):
            color = theme.CHANNEL_COLORS[i % 4]
            c = self.plot.plot(pen=pg.mkPen(color=color, width=1.5), name=f"ch{i + 1}")
            self._curves.append(c)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # 通道标签条
        self._labels_layout = QHBoxLayout()
        self._labels_layout.setContentsMargins(4, 0, 4, 0)
        self._labels_layout.setSpacing(8)
        self._labels: List[QLabel] = []
        for i in range(channels):
            lbl = QLabel(f"ch{i + 1}")
            self._restyle_label(lbl, i, visible=True)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.mousePressEvent = lambda evt, idx=i: self._toggle_ch(idx)
            self._labels.append(lbl)
            self._labels_layout.addWidget(lbl)
        self._labels_layout.addStretch(1)
        layout.addLayout(self._labels_layout)
        layout.addWidget(self.plot)

    def _restyle_label(self, lbl: QLabel, idx: int, visible: bool) -> None:
        L = theme.current()
        if visible:
            lbl.setStyleSheet(
                f"color:{theme.CHANNEL_COLORS[idx % 4]};font-weight:600;"
                f"padding:2px 6px;border-radius:4px;background:{L['bg_secondary']};"
            )
        else:
            lbl.setStyleSheet(
                f"color:{L['text_tertiary']};font-weight:400;"
                f"padding:2px 6px;border-radius:4px;background:{L['border_default']};"
            )

    def push_sample(self, ch_values) -> None:
        """喂入一个采样点（长度=channels）。"""
        self._t0 += 1.0 / self.fs
        self._t_ring.append(self._t0)
        for i, v in enumerate(ch_values):
            if i < self.channels:
                self._ring[i].append(float(v))
        self._refresh()

    def _refresh(self) -> None:
        n = len(self._t_ring)
        if n < 2:
            return
        ts = np.array(self._t_ring) - self._t0   # 0 在右
        for i in range(self.channels):
            if not self._ch_visible[i]:
                self._curves[i].setData([], [])
                continue
            ys = np.array(self._ring[i])
            self._curves[i].setData(ts, ys)

    def _toggle_ch(self, idx: int) -> None:
        self._ch_visible[idx] = not self._ch_visible[idx]
        self._restyle_label(self._labels[idx], idx, self._ch_visible[idx])
        self._refresh()

    def restyle(self) -> None:
        """主题切换时调用。"""
        L = theme.current()
        try:
            import pyqtgraph as pg
            pg.setConfigOptions(background=L["bg_primary"], foreground=L["text_primary"])
        except Exception:  # noqa: BLE001
            pass
        self.plot.setBackground(L["bg_primary"])
        for i, lbl in enumerate(self._labels):
            self._restyle_label(lbl, i, self._ch_visible[i])
        self.update()

    def clear(self) -> None:
        for d in self._ring:
            d.clear()
        self._t_ring.clear()
        self._t0 = 0.0
        for c in self._curves:
            c.setData([], [])
