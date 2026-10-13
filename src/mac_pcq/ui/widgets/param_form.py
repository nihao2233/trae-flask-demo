"""ParamForm：通用参数表单（参见 UI 设计 §6.7）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QPushButton, QHBoxLayout, QLineEdit, QLabel,
)

from mac_pcq.ui import theme


@dataclass
class FieldSpec:
    key: str
    label: str
    kind: str = "int"    # int / float / bool / choice / string
    choices: List[Tuple[str, Any]] = field(default_factory=list)
    min: float = 0
    max: float = 1_000_000
    step: float = 1
    unit: str = ""


class ParamForm(QWidget):
    apply_clicked = Signal()
    import_clicked = Signal()
    export_clicked = Signal()

    def __init__(self, fields: List[FieldSpec], parent=None) -> None:
        super().__init__(parent)
        L = theme.LIGHT
        self._fields = {f.key: f for f in fields}
        self._widgets: Dict[str, Any] = {}

        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for f in fields:
            if f.kind == "int":
                w = QSpinBox()
                w.setRange(int(f.min), int(f.max))
                w.setSingleStep(int(f.step))
            elif f.kind == "float":
                w = QDoubleSpinBox()
                w.setRange(f.min, f.max)
                w.setSingleStep(f.step)
                w.setDecimals(3)
            elif f.kind == "bool":
                w = QCheckBox()
            elif f.kind == "choice":
                w = QComboBox()
                for label, _ in f.choices:
                    w.addItem(label)
            elif f.kind == "string":
                w = QLineEdit()
            else:
                raise ValueError(f"unknown field kind: {f.kind}")
            w.setStyleSheet(
                f"QSpinBox,QDoubleSpinBox,QComboBox,QLineEdit{{padding:4px;border:1px solid {L['border_default']};"
                f"border-radius:4px;background:{L['bg_primary']};}}"
            )
            label = f.label + (f" ({f.unit})" if f.unit else "")
            layout.addRow(label, w)
            self._widgets[f.key] = w

        # 操作按钮
        row = QHBoxLayout()
        apply_btn = QPushButton("应用到设备")
        apply_btn.setStyleSheet(
            f"background:{L['brand_primary']};color:white;border:0;border-radius:4px;"
            f"padding:8px 16px;font-weight:600;"
        )
        apply_btn.clicked.connect(self.apply_clicked)
        export_btn = QPushButton("⤓  导出配置")
        export_btn.setStyleSheet(self._ghost_style())
        export_btn.clicked.connect(self.export_clicked)
        import_btn = QPushButton("⤒  导入配置")
        import_btn.setStyleSheet(self._ghost_style())
        import_btn.clicked.connect(self.import_clicked)
        row.addWidget(apply_btn)
        row.addStretch(1)
        row.addWidget(export_btn)
        row.addWidget(import_btn)
        layout.addRow("", _wrap(row))

    @staticmethod
    def _ghost_style() -> str:
        L = theme.LIGHT
        return (
            f"background:{L['bg_secondary']};color:{L['text_primary']};"
            f"border:1px solid {L['border_default']};border-radius:4px;padding:8px 16px;"
        )

    def set_values(self, values: Dict[str, Any]) -> None:
        for k, v in values.items():
            if k not in self._widgets:
                continue
            w = self._widgets[k]
            f = self._fields[k]
            if f.kind == "int":
                w.setValue(int(v))
            elif f.kind == "float":
                w.setValue(float(v))
            elif f.kind == "bool":
                w.setChecked(bool(v))
            elif f.kind == "choice":
                for i, (_, val) in enumerate(f.choices):
                    if val == v:
                        w.setCurrentIndex(i)
                        break
            elif f.kind == "string":
                w.setText(str(v))

    def get_values(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, w in self._widgets.items():
            f = self._fields[k]
            if f.kind == "int":
                out[k] = w.value()
            elif f.kind == "float":
                out[k] = w.value()
            elif f.kind == "bool":
                out[k] = w.isChecked()
            elif f.kind == "choice":
                idx = w.currentIndex()
                if 0 <= idx < len(f.choices):
                    out[k] = f.choices[idx][1]
            elif f.kind == "string":
                out[k] = w.text()
        return out


def _wrap(layout):
    w = QWidget()
    w.setLayout(layout)
    return w
