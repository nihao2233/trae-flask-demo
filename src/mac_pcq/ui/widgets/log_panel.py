"""LogPanel：日志表格 + 过滤（参见 UI 设计 §6.9）。"""

from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from mac_pcq.ui import theme

_LEVEL_COLOR = {
    "DEBUG": "#9A9A9A",
    "INFO": "#1F1F1F",
    "WARN": "#FF7A45",
    "ERROR": "#E5453D",
}


class LogPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        L = theme.LIGHT
        self._rows: List[Tuple[str, str, str]] = []   # (ts, level, msg)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        self._level_filter = QComboBox()
        self._level_filter.addItems(["全部", "DEBUG", "INFO", "WARN", "ERROR"])
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索关键字…")
        bar.addWidget(self._level_filter)
        bar.addWidget(self._search, 1)
        layout.addLayout(bar)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["时间", "级别", "消息"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, 1)

        self.setStyleSheet(
            f"QTableWidget{{background:{L['bg_primary']};gridline-color:{L['border_default']};}}"
            f"QHeaderView::section{{background:{L['bg_secondary']};color:{L['text_primary']};"
            f"padding:4px;border:0;border-right:1px solid {L['border_default']};}}"
        )

    def append_log(self, ts: str, level: str, msg: str) -> None:
        self._rows.append((ts, level, msg))
        self._refresh()

    def _refresh(self) -> None:
        level_filter = self._level_filter.currentText()
        keyword = self._search.text().lower().strip()
        rows = [
            (ts, lv, m) for (ts, lv, m) in self._rows
            if (level_filter == "全部" or lv == level_filter)
            and (not keyword or keyword in m.lower() or keyword in lv.lower())
        ]
        self._table.setRowCount(len(rows))
        for r, (ts, lv, m) in enumerate(rows):
            c1 = QTableWidgetItem(ts)
            c2 = QTableWidgetItem(lv)
            c3 = QTableWidgetItem(m)
            c2.setForeground(QColor(_LEVEL_COLOR.get(lv, "#1F1F1F")))
            self._table.setItem(r, 0, c1)
            self._table.setItem(r, 1, c2)
            self._table.setItem(r, 2, c3)
