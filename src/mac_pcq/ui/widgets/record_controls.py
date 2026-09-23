"""RecordControls：录制 / 停止 / 导出按钮组（参见 UI 设计 §6.5）。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

from mac_pcq.ui import theme


class RecordControls(QWidget):
    start_clicked = Signal()
    stop_clicked = Signal()
    export_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.LIGHT
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.start_btn = QPushButton("⏺  开始录制")
        self.start_btn.setStyleSheet(
            f"background:{L['accent_danger']};color:white;border:0;"
            f"border-radius:4px;padding:8px 16px;font-weight:600;"
        )
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self.start_clicked)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹  停止")
        self.stop_btn.setStyleSheet(
            f"background:{L['bg_secondary']};color:{L['text_primary']};"
            f"border:1px solid {L['border_default']};border-radius:4px;"
            f"padding:8px 16px;font-weight:600;"
        )
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton("⤓  导出 CSV")
        self.export_btn.setStyleSheet(
            f"background:{L['brand_primary']};color:white;border:0;"
            f"border-radius:4px;padding:8px 16px;font-weight:600;"
        )
        self.export_btn.setFixedHeight(40)
        self.export_btn.clicked.connect(self.export_clicked)
        layout.addWidget(self.export_btn)
        layout.addStretch(1)

    def set_recording(self, on: bool) -> None:
        self.start_btn.setEnabled(not on)
        self.stop_btn.setEnabled(on)
