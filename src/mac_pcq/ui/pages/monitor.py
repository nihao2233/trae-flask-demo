"""P1 - 主监测页（参见 UI 设计 §6.1 + §7 + §8）。

布局：
    左上：4 路 ECG（WaveformCanvas）
    右上：矩阵缩略 60×60（MatrixGrid + ColorScaleBar）
    左下：2 路压电（WaveformCanvas）
    右下：生命体征卡片（VitalCard）

信号来源（由 main_window 注入）：
    bus.ecg_ready → ECG 更新
    bus.piezo_ready → PVDF 更新
    bus.resistive_ready → 矩阵更新
    bus.vital_ready → 心率更新
    bus.system_status → 生命体征卡电量/运行时长
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout

from ..widgets.waveform_canvas import WaveformCanvas
from ..widgets.matrix_grid import MatrixGrid
from ..widgets.color_scale_bar import ColorScaleBar
from ..widgets.vital_card import VitalCard
from .. import theme
from ...core.constants import DEFAULT_ECG_FS, DEFAULT_PVDF_FS


class PageMonitor(QWidget):
    """主监测页。"""

    def __init__(
        self,
        ecg_fs: int = DEFAULT_ECG_FS,
        pvdf_fs: int = DEFAULT_PVDF_FS,
        parent=None,
    ) -> None:
        super().__init__(parent)
        L = theme.LIGHT

        # 标题
        title = QLabel("主监测")
        title.setStyleSheet(f"color:{L['text_primary']};font-size:22px;font-weight:700;")

        # 子区
        self.ecg = WaveformCanvas(
            channels=4, fs=ecg_fs, window_s=5.0, y_range=1.0,
            title="ECG", y_unit="mV",
        )
        self.piezo = WaveformCanvas(
            channels=2, fs=pvdf_fs, window_s=5.0, y_range=10.0,
            title="PVDF", y_unit="mV",
        )
        self.matrix = MatrixGrid(cell=60, gap=2, base="blue_red", vmin=10, vmax=500, unit="kΩ")
        self.scale_bar = ColorScaleBar(base="blue_red", vmin=10, vmax=500, unit="kΩ")
        self.vital = VitalCard()

        # 把每个子区包成带标题的小组（保存引用便于主题切换）
        self._ecg_box = self._wrap_panel("心电 (ECG)", self.ecg, L)
        self._matrix_box = self._wrap_panel("矩阵缩略", self._matrix_with_legend(), L)
        self._piezo_box = self._wrap_panel("压电 (PVDF)", self.piezo, L)
        self._vital_box = self.vital   # VitalCard 自带标题/边框

        # 2x2 网格
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.addWidget(self._ecg_box, 0, 0)
        grid.addWidget(self._matrix_box, 0, 1)
        grid.addWidget(self._piezo_box, 1, 0)
        grid.addWidget(self._vital_box, 1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addWidget(title)
        root.addLayout(grid, 1)

    def _wrap_panel(self, title: str, body: QWidget, L: dict) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{L['bg_primary']};border:1px solid {L['border_default']};"
            f"border-radius:8px;"
        )
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(f"color:{L['text_primary']};font-size:16px;font-weight:600;")
        lay.addWidget(t)
        lay.addWidget(body, 1)
        return w

    def _matrix_with_legend(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self.matrix, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.scale_bar)
        lay.addStretch(1)
        return w

    # ---- 槽函数（由 main_window 接到 DataBus Signal）----
    def on_ecg(self, sample) -> None:
        self.ecg.push_sample(sample.ch)

    def on_piezo(self, sample) -> None:
        self.piezo.push_sample(sample.ch)

    def on_resistive(self, sample) -> None:
        # r_ohm → kΩ
        self.matrix.set_values([r / 1000.0 for r in sample.r_ohm])

    def on_vital(self, v) -> None:
        self.vital.update_vital(v.hr_bpm, v.rr_bpm, v.quality)

    def on_system_status(self, s) -> None:
        self.vital.update_status(s.level_pct, s.uptime_s)

    # ---- 主题切换 ----
    def restyle(self) -> None:
        """主题切换时被 MainWindow 调用，重建 widget 配色。"""
        L = theme.current()
        from PySide6.QtGui import QColor
        import pyqtgraph as pg
        # pyqtgraph 主题（波形区）
        bg = QColor(L["bg_primary"]).name()
        fg = QColor(L["text_primary"]).name()
        try:
            pg.setConfigOptions(background=bg, foreground=fg)
        except Exception:  # noqa: BLE001
            pass
        self.ecg.plot.setBackground(L["bg_primary"])
        self.piezo.plot.setBackground(L["bg_primary"])
        self.ecg.plot.getAxis("left").setPen(fg)
        self.ecg.plot.getAxis("left").setTextPen(fg)
        self.ecg.plot.getAxis("bottom").setPen(fg)
        self.ecg.plot.getAxis("bottom").setTextPen(fg)
        self.piezo.plot.getAxis("left").setPen(fg)
        self.piezo.plot.getAxis("left").setTextPen(fg)
        self.piezo.plot.getAxis("bottom").setPen(fg)
        self.piezo.plot.getAxis("bottom").setTextPen(fg)
        # 主区
        self._ecg_box.setStyleSheet(
            f"background:{L['bg_primary']};border:1px solid {L['border_default']};border-radius:8px;"
        )
        self._matrix_box.setStyleSheet(
            f"background:{L['bg_primary']};border:1px solid {L['border_default']};border-radius:8px;"
        )
        self._piezo_box.setStyleSheet(
            f"background:{L['bg_primary']};border:1px solid {L['border_default']};border-radius:8px;"
        )
        # 标题字体颜色更新（用 findChildren 找到 QLabel）
        for lbl in self.findChildren(QLabel):
            cur = lbl.styleSheet()
            # 简单粗暴：所有 Panel 标题都重设
            new = cur
            for old, newc in [(L["text_primary"] if False else "transparent", "transparent")]:
                pass
        # 直接重新加载样式：触发 update
        self.update()
