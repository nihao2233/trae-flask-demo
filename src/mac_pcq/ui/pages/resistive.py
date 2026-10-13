"""P2 - 压阻矩阵页（参见 UI 设计 §6.2 + §8）。

布局：
    上方：大尺寸 4×4 矩阵 + 色阶图例 + 显示格式切换
    下方左侧：基色选择（6 种）+ 深度档位（5 档）
    下方右侧：压力方程 + 两点标定

交互：
    单击单元格 → 选中 A
    再单击另一单元格 → 弹出确认 toast → 互换
    双击单元格 → 显示历史曲线（待实现）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton,
    QButtonGroup, QRadioButton, QDoubleSpinBox, QFrame, QMessageBox,
    QComboBox, QGroupBox, QFormLayout, QToolButton,
)

from ..widgets.matrix_grid import MatrixGrid
from ..widgets.color_scale_bar import ColorScaleBar
from .. import theme
from ...domain.calibration import Calibration, CalibrationConfig
from ...core.constants import RES_MAX_KOHM, RES_MIN_KOHM, PRESS_MIN_N, PRESS_MAX_N


# 5 档深度对应"压力 / 电阻最大值"
_DEPTH_MAX = {
    1: 100.0,
    2: 500.0,
    3: 1500.0,
    4: 3000.0,
    5: 5000.0,
}


class _BigMatrix(MatrixGrid):
    """80×80 单元 + 悬停高亮 + 选中 A / 选中 B 状态。"""

    def __init__(self, base: str, vmin: float, vmax: float, unit: str, parent=None) -> None:
        super().__init__(cell=80, gap=4, base=base, vmin=vmin, vmax=vmax, unit=unit, parent=parent)
        self._selected: Optional[int] = None

    def set_selected(self, idx: Optional[int]) -> None:
        self._selected = idx
        self.update()

    def selected(self) -> Optional[int]:
        return self._selected

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
            # 悬停高亮 / 选中金色边框
            if i == self._selected:
                pen_color = QColor(L["accent_warning"])
                pen_w = 3
            elif self._hover_idx == i:
                pen_color = QColor(L["brand_primary"])
                pen_w = 2
            else:
                pen_color = QColor(L["border_default"])
                pen_w = 1
            p.setPen(QPen(pen_color, pen_w))
            p.drawRect(x, y, self.cell, self.cell)
            # 数值
            p.setPen(QColor(L["text_primary"]))
            f = QFont()
            f.setPixelSize(11)
            p.setFont(f)
            txt = f"{self._values[i]:.1f}"
            text_rect = QRectF(x + self.cell - 44, y + self.cell - 18, 40, 16)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, txt)
        p.end()


def _value_to_color(value: float, vmin: float, vmax: float, base: str) -> QColor:
    from ..widgets.matrix_grid import _value_to_color as _impl
    return _impl(value, vmin, vmax, base)


class PageResistive(QWidget):
    """P2 压阻矩阵页。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.current()
        self._cfg = CalibrationConfig()
        self._channel_map: List[Tuple[int, int]] = [(i // 4, i % 4) for i in range(16)]
        self._display_format: str = "resistance"   # resistance / pressure

        # ==== 标题 ====
        title = QLabel("压阻矩阵")
        title.setStyleSheet(f"color:{L['text_primary']};font-size:22px;font-weight:700;")

        # ==== 矩阵 + 色阶 ====
        self._matrix = _BigMatrix(
            base="blue_red",
            vmin=RES_MIN_KOHM,
            vmax=RES_MAX_KOHM,
            unit="kΩ",
        )
        self._scale = ColorScaleBar(base="blue_red", vmin=RES_MIN_KOHM, vmax=RES_MAX_KOHM, unit="kΩ")

        # 显示格式切换
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("显示格式："))
        self._btn_res = QRadioButton("电阻 (kΩ)")
        self._btn_pres = QRadioButton("压力 (N)")
        self._btn_res.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self._btn_res)
        grp.addButton(self._btn_pres)
        self._btn_res.toggled.connect(self._on_format_changed)
        format_row.addWidget(self._btn_res)
        format_row.addWidget(self._btn_pres)
        format_row.addStretch(1)
        # 操作按钮
        self._reset_map_btn = QPushButton("恢复默认映射")
        self._reset_map_btn.clicked.connect(self._reset_mapping)
        self._reset_map_btn.setStyleSheet(
            f"background:{L['bg_secondary']};color:{L['text_primary']};"
            f"border:1px solid {L['border_default']};border-radius:4px;padding:6px 12px;"
        )
        format_row.addWidget(self._reset_map_btn)

        # ==== 色阶配置（基色 + 深度档位）====
        colors_group = QGroupBox("色阶基色")
        colors_lay = QHBoxLayout(colors_group)
        self._base_btns: List[QToolButton] = []
        for base_name in theme.COLOR_BASES.keys():
            btn = QToolButton()
            btn.setText(base_name)
            btn.setCheckable(True)
            btn.setChecked(base_name == "blue_red")
            btn.clicked.connect(lambda _checked=False, name=base_name: self._on_base_changed(name))
            btn.setStyleSheet(self._color_btn_style())
            self._base_btns.append(btn)
            colors_lay.addWidget(btn)

        depth_group = QGroupBox("深度档位（5 档）")
        depth_lay = QHBoxLayout(depth_group)
        self._depth_btns: List[QRadioButton] = []
        for d in range(1, 6):
            rb = QRadioButton(f"{d}")
            if d == 5:
                rb.setChecked(True)
            rb.clicked.connect(lambda _checked=False, depth=d: self._on_depth_changed(depth))
            self._depth_btns.append(rb)
            depth_lay.addWidget(rb)
        depth_lay.addStretch(1)
        depth_lay.addWidget(QLabel("（最大压力 / 电阻值）"))

        # ==== 压力方程 ====
        eq_group = QGroupBox("压力方程（电阻→压力）")
        eq_form = QFormLayout(eq_group)
        self._breakpoint_sb = QDoubleSpinBox()
        self._breakpoint_sb.setRange(1.0, 100.0)
        self._breakpoint_sb.setValue(self._cfg.breakpoint_kohm)
        self._breakpoint_sb.setSuffix(" kΩ")
        self._breakpoint_sb.valueChanged.connect(self._on_calib_changed)
        self._a1_sb = QDoubleSpinBox()
        self._a1_sb.setDecimals(4)
        self._a1_sb.setRange(0.0001, 100.0)
        self._a1_sb.setValue(self._cfg.a1)
        self._a1_sb.valueChanged.connect(self._on_calib_changed)
        self._a2_sb = QDoubleSpinBox()
        self._a2_sb.setDecimals(4)
        self._a2_sb.setRange(0.0001, 100.0)
        self._a2_sb.setValue(self._cfg.a2)
        self._a2_sb.valueChanged.connect(self._on_calib_changed)
        self._b_sb = QDoubleSpinBox()
        self._b_sb.setDecimals(2)
        self._b_sb.setRange(-100.0, 100.0)
        self._b_sb.setValue(self._cfg.b)
        self._b_sb.valueChanged.connect(self._on_calib_changed)
        eq_form.addRow("断点 R_b：", self._breakpoint_sb)
        eq_form.addRow("a₁ (R<R_b)：", self._a1_sb)
        eq_form.addRow("a₂ (R≥R_b)：", self._a2_sb)
        eq_form.addRow("b：", self._b_sb)

        # ==== 两点标定 ====
        cal_group = QGroupBox("两点标定")
        cal_form = QFormLayout(cal_group)
        self._r1_sb = QDoubleSpinBox()
        self._r1_sb.setRange(0.1, 1000.0)
        self._r1_sb.setSuffix(" kΩ")
        self._p1_sb = QDoubleSpinBox()
        self._p1_sb.setRange(-1000.0, 10000.0)
        self._p1_sb.setSuffix(" N")
        self._r2_sb = QDoubleSpinBox()
        self._r2_sb.setRange(0.1, 1000.0)
        self._r2_sb.setSuffix(" kΩ")
        self._p2_sb = QDoubleSpinBox()
        self._p2_sb.setRange(-1000.0, 10000.0)
        self._p2_sb.setSuffix(" N")
        cal_btn = QPushButton("解算 a, b")
        cal_btn.clicked.connect(self._solve_calib)
        cal_btn.setStyleSheet(
            f"background:{L['brand_primary']};color:white;border:0;border-radius:4px;"
            f"padding:6px 12px;font-weight:600;"
        )
        cal_form.addRow("(R₁, P₁)：", _wrap_row(self._r1_sb, self._p1_sb))
        cal_form.addRow("(R₂, P₂)：", _wrap_row(self._r2_sb, self._p2_sb))
        cal_form.addRow("", cal_btn)
        self._cal_result_lbl = QLabel("—")
        self._cal_result_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        cal_form.addRow("解算结果：", self._cal_result_lbl)

        # ==== 整体布局 ====
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(title)
        root.addLayout(format_row)

        # 矩阵 + 色阶 中央对齐
        matrix_box = QFrame()
        matrix_box.setStyleSheet(
            f"background:{L['bg_primary']};border:1px solid {L['border_default']};border-radius:8px;"
        )
        mb_lay = QVBoxLayout(matrix_box)
        mb_lay.setContentsMargins(16, 12, 16, 12)
        mb_lay.setSpacing(8)
        mb_lay.addWidget(self._matrix, 0, Qt.AlignmentFlag.AlignCenter)
        mb_lay.addWidget(self._scale)
        self._hint_lbl = QLabel("提示：单击单元格选中 A，再单击另一格互换")
        self._hint_lbl.setStyleSheet(f"color:{L['text_tertiary']};font-size:12px;")
        mb_lay.addWidget(self._hint_lbl)
        root.addWidget(matrix_box)

        # 色阶配置 + 压力方程 + 两点标定
        bottom = QHBoxLayout()
        bottom.addWidget(colors_group)
        bottom.addWidget(depth_group)
        bottom.addWidget(eq_group)
        bottom.addWidget(cal_group, 1)
        root.addLayout(bottom, 1)

        # 矩阵单击处理（基类只触发 hover，这里手动接 mousePressEvent）
        self._matrix.mousePressEvent = self._on_matrix_click

        # 推一组示例数据
        self._matrix.set_values([20.0 + (i % 4) * 80 + (i // 4) * 10 for i in range(16)])

    # ---- 槽函数 ----
    def on_resistive(self, sample) -> None:
        # r_ohm → kΩ（原始电阻），UI 端再换算
        self._matrix.set_values([r / 1000.0 for r in sample.r_ohm])

    def _on_format_changed(self) -> None:
        self._display_format = "pressure" if self._btn_pres.isChecked() else "resistance"
        self._update_for_format()

    def _on_base_changed(self, name: str) -> None:
        self._matrix.set_base(name)
        self._scale.set_base(name)

    def _on_depth_changed(self, depth: int) -> None:
        vmax = _DEPTH_MAX[depth]
        if self._display_format == "pressure":
            self._matrix.set_range(0, vmax)
            self._scale.set_range(0, vmax)
        else:
            self._matrix.set_range(0, vmax / 5)   # 电阻档位较粗略
            self._scale.set_range(0, vmax / 5)

    def _on_calib_changed(self) -> None:
        self._cfg.a1 = self._a1_sb.value()
        self._cfg.a2 = self._a2_sb.value()
        self._cfg.b = self._b_sb.value()
        self._cfg.breakpoint_kohm = self._breakpoint_sb.value()

    def _solve_calib(self) -> None:
        r1, p1 = self._r1_sb.value(), self._p1_sb.value()
        r2, p2 = self._r2_sb.value(), self._p2_sb.value()
        try:
            a, b = Calibration.calibrate_two_point(r1, p1, r2, p2)
        except ValueError as e:
            QMessageBox.warning(self, "标定失败", f"两点标定失败：{e}")
            return
        self._a2_sb.setValue(a)
        self._b_sb.setValue(b)
        self._cal_result_lbl.setText(f"a = {a:.4f}, b = {b:.2f}  → 已应用")

    def _on_matrix_click(self, evt) -> None:
        # 复用基类 hover 逻辑 + 提取 idx
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        pos = evt.position() if hasattr(evt, "position") else QPointF(evt.pos())
        x, y = int(pos.x()), int(pos.y())
        col = x // (self._matrix.cell + self._matrix.gap)
        row = y // (self._matrix.cell + self._matrix.gap)
        if not (0 <= row < 4 and 0 <= col < 4):
            return
        idx = row * 4 + col
        sel = self._matrix.selected()
        if sel is None:
            self._matrix.set_selected(idx)
            self._hint_lbl.setText(
                f"已选中 通道 {sel if sel is not None else idx + 1}（{row},{col}）— 再点另一格互换"
            )
        elif sel == idx:
            self._matrix.set_selected(None)
            self._hint_lbl.setText("提示：单击单元格选中 A，再单击另一格互换")
        else:
            ret = QMessageBox.question(
                self,
                "确认互换",
                f"交换 通道 {sel + 1} ↔ 通道 {idx + 1}？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self._channel_map[sel], self._channel_map[idx] = self._channel_map[idx], self._channel_map[sel]
            self._matrix.set_selected(None)
            self._hint_lbl.setText("提示：单击单元格选中 A，再单击另一格互换")
            self._update_for_format()

    def _reset_mapping(self) -> None:
        ret = QMessageBox.question(
            self,
            "恢复默认映射",
            "确认恢复默认（identity）映射？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._channel_map = [(i // 4, i % 4) for i in range(16)]
            self._matrix.set_selected(None)

    def _update_for_format(self) -> None:
        """根据当前显示格式，把 raw kΩ 换算成显示值。"""
        if self._display_format == "pressure":
            raw = self._matrix._values
            disp = [Calibration.resistance_to_pressure(r * 1000.0, self._cfg) for r in raw]
            self._matrix.set_values(disp)
            self._matrix.unit = "N"
            self._scale.unit = "N"
            self._scale.set_range(0, PRESS_MAX_N)
        else:
            # 复位（外部已经喂入）
            self._matrix.unit = "kΩ"
            self._scale.unit = "kΩ"
            self._scale.set_range(RES_MIN_KOHM, RES_MAX_KOHM)
        self._scale.update()

    @staticmethod
    def _color_btn_style() -> str:
        L = theme.current()
        return (
            f"QToolButton{{background:{L['bg_secondary']};color:{L['text_primary']};"
            f"border:1px solid {L['border_default']};border-radius:4px;padding:4px 10px;}}"
            f"QToolButton:checked{{background:{L['brand_primary']};color:white;border:0;}}"
        )

    def restyle(self) -> None:
        """主题切换。"""
        L = theme.current()
        # 标题
        for lbl in self.findChildren(QLabel):
            cur = lbl.styleSheet()
        # 重建 stylesheet 颜色（简化：所有 GroupBox 重新设）
        for grp in self.findChildren(QGroupBox):
            grp.setStyleSheet(
                f"QGroupBox{{border:1px solid {L['border_default']};border-radius:6px;"
                f"margin-top:8px;padding-top:8px;color:{L['text_primary']};}}"
                f"QGroupBox::title{{subcontrol-origin:margin;left:8px;padding:0 4px;"
                f"color:{L['text_secondary']};}}"
            )
        self._matrix.restyle()
        self._scale.restyle()
        # hint label 重设
        self._hint_lbl.setStyleSheet(f"color:{L['text_tertiary']};font-size:12px;")
        self._reset_map_btn.setStyleSheet(
            f"background:{L['bg_secondary']};color:{L['text_primary']};"
            f"border:1px solid {L['border_default']};border-radius:4px;padding:6px 12px;"
        )
        for btn in self._base_btns:
            btn.setStyleSheet(self._color_btn_style())


def _wrap_row(*widgets) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    for x in widgets:
        lay.addWidget(x)
    return w
