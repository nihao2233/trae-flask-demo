"""UpgradeProgress：升级进度条（参见 UI 设计 §6.8）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QHBoxLayout, QPushButton

from mac_pcq.ui import theme


class UpgradeProgress(QWidget):
    start_clicked = Signal()
    cancel_clicked = Signal()

    _STATE_LABEL = {
        "idle": "等待开始",
        "checking": "校验中",
        "upgrading": "升级中",
        "writing": "写入中",
        "success": "升级成功",
        "failed": "升级失败",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.LIGHT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._state_lbl = QLabel("状态：等待开始")
        self._state_lbl.setStyleSheet(f"color:{L['text_primary']};font-size:14px;font-weight:600;")
        layout.addWidget(self._state_lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(20)
        self._bar.setStyleSheet(
            f"QProgressBar{{border:1px solid {L['border_default']};border-radius:4px;"
            f"text-align:center;background:{L['bg_secondary']};}}"
            f"QProgressBar::chunk{{background:{L['brand_primary']};border-radius:3px;}}"
        )
        layout.addWidget(self._bar)

        bar = QHBoxLayout()
        self._start_btn = QPushButton("开始升级")
        self._start_btn.setStyleSheet(
            f"background:{L['brand_primary']};color:white;border:0;border-radius:4px;"
            f"padding:8px 16px;font-weight:600;"
        )
        self._start_btn.clicked.connect(self.start_clicked)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setStyleSheet(
            f"background:{L['bg_secondary']};color:{L['text_primary']};"
            f"border:1px solid {L['border_default']};border-radius:4px;padding:8px 16px;"
        )
        self._cancel_btn.clicked.connect(self.cancel_clicked)
        bar.addWidget(self._start_btn)
        bar.addStretch(1)
        bar.addWidget(self._cancel_btn)
        layout.addLayout(bar)

    def set_progress(self, percent: int, state: str = "upgrading") -> None:
        self._bar.setValue(percent)
        self._state_lbl.setText(f"状态：{self._STATE_LABEL.get(state, state)}  {percent}%")

    def reset(self) -> None:
        self._bar.setValue(0)
        self._state_lbl.setText("状态：等待开始")
