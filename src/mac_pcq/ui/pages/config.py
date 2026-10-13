"""P7 - 参数配置页（参见 UI 设计 §6.7）。

- 采样率（ECG/PVDF/Res）
- 滤波窗
- 标定系数
- 通道映射（查看 + 重置）
- 应用 / 导出 / 导入
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QDoubleSpinBox, QSpinBox, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem,
)

from .. import theme
from ..widgets.param_form import FieldSpec, ParamForm
from ...domain.calibration import CalibrationConfig
from ...core.constants import DEFAULT_ECG_FS, DEFAULT_PVDF_FS, DEFAULT_RESISTIVE_FS
from ...protocol.commands import CommandBuilder
from ...platform.paths import user_data_dir


class PageConfig(QWidget):
    """P7 参数配置页。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.current()

        self._cfg = CalibrationConfig()
        self._send_cmd = lambda b: None    # 由 AppController 注入

        # ==== 标题 ====
        title = QLabel("参数配置")
        title.setStyleSheet(f"color:{L['text_primary']};font-size:22px;font-weight:700;")

        # ==== 采样率 / 滤波 / 标定（ParamForm）====
        fields = [
            FieldSpec("ecg_fs", "ECG 采样率", kind="int",
                      min=50, max=2000, step=50, unit="Hz"),
            FieldSpec("pvdf_fs", "PVDF 采样率", kind="int",
                      min=50, max=2000, step=50, unit="Hz"),
            FieldSpec("res_fs", "压阻采样率", kind="int",
                      min=1, max=200, step=1, unit="Hz"),
            FieldSpec("ecg_filter_window", "ECG 滤波窗", kind="int",
                      min=1, max=21, step=2),
            FieldSpec("hr_period", "HR 上报周期", kind="int",
                      min=1, max=60, step=1, unit="s"),
            FieldSpec("breakpoint_kohm", "压力方程断点", kind="float",
                      min=0.1, max=100.0, step=0.1, unit="kΩ"),
            FieldSpec("a1", "压力方程 a₁", kind="float",
                      min=0.0001, max=100.0, step=0.001),
            FieldSpec("a2", "压力方程 a₂", kind="float",
                      min=0.0001, max=100.0, step=0.001),
            FieldSpec("b", "压力方程 b", kind="float",
                      min=-100.0, max=100.0, step=0.1),
        ]
        self._form = ParamForm(fields)
        self._form.set_values({
            "ecg_fs": DEFAULT_ECG_FS,
            "pvdf_fs": DEFAULT_PVDF_FS,
            "res_fs": DEFAULT_RESISTIVE_FS,
            "ecg_filter_window": 3,
            "hr_period": 1,
            "breakpoint_kohm": self._cfg.breakpoint_kohm,
            "a1": self._cfg.a1,
            "a2": self._cfg.a2,
            "b": self._cfg.b,
        })
        self._form.apply_clicked.connect(self._on_apply)

        # ==== 通道映射（轻量展示） ====
        map_group = QGroupBox("通道映射（4×4，identity）")
        map_lay = QVBoxLayout(map_group)
        info = QLabel("通道 i 默认映射到显示位置 (i//4, i%4)。"
                      "如需互换，请到 压阻矩阵 页操作。")
        info.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        info.setWordWrap(True)
        map_lay.addWidget(info)
        # 16 行通道预览
        self._map_list = QListWidget()
        for i in range(16):
            self._map_list.addItem(QListWidgetItem(f"通道 {i + 1}  →  ({i // 4}, {i % 4})"))
        self._map_list.setMaximumHeight(180)
        map_lay.addWidget(self._map_list)

        # ==== 操作按钮 ====
        op_row = QHBoxLayout()
        self._import_btn = QPushButton("⤒  导入配置")
        self._export_btn = QPushButton("⤓  导出配置")
        self._reset_btn = QPushButton("恢复默认值")
        for btn in (self._import_btn, self._export_btn, self._reset_btn):
            btn.setStyleSheet(
                f"background:{L['bg_secondary']};color:{L['text_primary']};"
                f"border:1px solid {L['border_default']};border-radius:4px;padding:8px 16px;"
            )
            op_row.addWidget(btn)
        op_row.addStretch(1)
        self._import_btn.clicked.connect(self._on_import)
        self._export_btn.clicked.connect(self._on_export)
        self._reset_btn.clicked.connect(self._on_reset)

        # ==== 布局 ====
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addWidget(title)

        bottom = QHBoxLayout()
        bottom.addWidget(self._form, 2)
        bottom.addWidget(map_group, 1)
        root.addLayout(bottom, 1)

        root.addLayout(op_row)

    # ---- 应用 ----
    def _on_apply(self) -> None:
        v = self._form.get_values()
        # 校验
        try:
            self._cfg = CalibrationConfig(
                a1=v["a1"], a2=v["a2"], b=v["b"],
                breakpoint_kohm=v["breakpoint_kohm"],
            )
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "参数无效", str(e))
            return

        # 下发命令
        try:
            for cmd in (
                CommandBuilder.set_ecg_fs(v["ecg_fs"]),
                CommandBuilder.set_pvdf_fs(v["pvdf_fs"]),
                CommandBuilder.set_res_fs(v["res_fs"]),
                CommandBuilder.set_hr_period(v["hr_period"]),
            ):
                self._send_cmd(cmd)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "下发失败", f"参数下发失败：{e}")
            return

        QMessageBox.information(
            self, "已应用",
            f"参数已下发到设备：\nECG={v['ecg_fs']}Hz / PVDF={v['pvdf_fs']}Hz / "
            f"Res={v['res_fs']}Hz / HR_period={v['hr_period']}s\n"
            f"标定：a₁={v['a1']}, a₂={v['a2']}, b={v['b']}, 断点={v['breakpoint_kohm']} kΩ"
        )

    # ---- 导入 ----
    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", user_data_dir(), "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._form.set_values({k: data[k] for k in data if k in [
                "ecg_fs", "pvdf_fs", "res_fs", "ecg_filter_window",
                "hr_period", "breakpoint_kohm", "a1", "a2", "b",
            ]})
            QMessageBox.information(self, "导入成功", f"已导入：{os.path.basename(path)}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "导入失败", str(e))

    # ---- 导出 ----
    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", os.path.join(user_data_dir(), "config.json"),
            "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._form.get_values(), f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已保存到：{path}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "导出失败", str(e))

    # ---- 重置 ----
    def _on_reset(self) -> None:
        ret = QMessageBox.question(
            self, "恢复默认", "确认恢复所有参数为默认值？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._form.set_values({
                "ecg_fs": DEFAULT_ECG_FS,
                "pvdf_fs": DEFAULT_PVDF_FS,
                "res_fs": DEFAULT_RESISTIVE_FS,
                "ecg_filter_window": 3,
                "hr_period": 1,
                "breakpoint_kohm": 10.0,
                "a1": 0.01,
                "a2": 0.005,
                "b": 25.0,
            })

    def set_send_cmd(self, cb) -> None:
        """由 AppController 注入，用于下发命令。"""
        self._send_cmd = cb

    def restyle(self) -> None:
        L = theme.current()
        for grp in self.findChildren(QGroupBox):
            grp.setStyleSheet(
                f"QGroupBox{{border:1px solid {L['border_default']};border-radius:6px;"
                f"margin-top:8px;padding-top:8px;color:{L['text_primary']};}}"
                f"QGroupBox::title{{subcontrol-origin:margin;left:8px;padding:0 4px;"
                f"color:{L['text_secondary']};}}"
            )
        for btn in (self._import_btn, self._export_btn, self._reset_btn):
            btn.setStyleSheet(
                f"background:{L['bg_secondary']};color:{L['text_primary']};"
                f"border:1px solid {L['border_default']};border-radius:4px;padding:8px 16px;"
            )
