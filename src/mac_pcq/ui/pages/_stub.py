"""P2~P9 页面的 stub 基类（统一外观）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from .. import theme


class StubPage(QWidget):
    """通用占位页（避免每个 page 单独写）。"""

    TITLE: str = "Stub"
    DESC: str = "本页面将在后续迭代中实现"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.current()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self._title = QLabel(self.TITLE)
        self._title.setStyleSheet(
            f"color:{L['text_primary']};font-size:22px;font-weight:700;"
        )
        layout.addWidget(self._title)
        self._desc = QLabel(self.DESC)
        self._desc.setStyleSheet(f"color:{L['text_secondary']};font-size:14px;")
        self._desc.setWordWrap(True)
        layout.addWidget(self._desc)
        layout.addStretch(1)

    def restyle(self) -> None:
        L = theme.current()
        self._title.setStyleSheet(
            f"color:{L['text_primary']};font-size:22px;font-weight:700;"
        )
        self._desc.setStyleSheet(f"color:{L['text_secondary']};font-size:14px;")
