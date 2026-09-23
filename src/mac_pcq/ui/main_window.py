"""MainWindow：顶栏 + 左侧导航 + 主区 + 底栏（参见 UI 设计 §4.1 / §11.1）。

快捷键：Ctrl+O / Ctrl+S / Ctrl+E / F1 / F5 / Esc / 1~9（§10.3）
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem,
    QFrame, QStatusBar,
)

from .widgets.link_indicator import LinkIndicator
from .widgets.status_badge import StatusBadge
from .pages.monitor import PageMonitor
from .pages.resistive import PageResistive
from .pages.piezo import PagePiezo
from .pages.vital import PageVital
from .pages.record import PageRecord
from .pages.device import PageDevice
from .pages.config import PageConfig
from .pages.upgrade import PageUpgrade
from .pages.log import PageLog
from . import theme


_NAV = [
    ("主监测", PageMonitor),
    ("压阻矩阵", PageResistive),
    ("压电波形", PagePiezo),
    ("生命体征", PageVital),
    ("记录回放", PageRecord),
    ("设备状态", PageDevice),
    ("参数配置", PageConfig),
    ("固件升级", PageUpgrade),
    ("日志", PageLog),
]


class MainWindow(QMainWindow):
    def __init__(self, app_controller=None, parent=None) -> None:
        super().__init__(parent)
        self.app = app_controller
        self.setWindowTitle("多模态采集板上住机 v0.1")
        self.resize(1280, 800)

        L = theme.current()
        self.setStyleSheet(
            f"QMainWindow{{background:{L['bg_primary']};}}"
            f"QListWidget{{background:{L['bg_secondary']};border:0;outline:0;}}"
            f"QListWidget::item{{padding:12px 16px;color:{L['text_primary']};}}"
            f"QListWidget::item:selected{{background:{L['brand_primary']};color:white;}}"
            f"QStatusBar{{background:{L['bg_secondary']};color:{L['text_secondary']};}}"
        )

        # ---- 顶栏 ----
        topbar = QWidget()
        topbar.setFixedHeight(56)
        topbar.setStyleSheet(
            f"background:{L['bg_primary']};border-bottom:1px solid {L['border_default']};"
        )
        top_lay = QHBoxLayout(topbar)
        top_lay.setContentsMargins(16, 0, 16, 0)
        logo = QLabel("● 多模态采集板上住机")
        logo.setStyleSheet(f"color:{L['text_primary']};font-size:16px;font-weight:700;")
        top_lay.addWidget(logo)
        top_lay.addStretch(1)
        self.link_ind = LinkIndicator()
        top_lay.addWidget(self.link_ind)
        self.status_badge = StatusBadge()
        top_lay.addWidget(self.status_badge)
        theme_btn = QPushButton("◐")
        theme_btn.setToolTip("切换主题（浅色 / 深色）")
        theme_btn.setStyleSheet(f"border:0;background:transparent;font-size:18px;padding:0 8px;")
        theme_btn.clicked.connect(self._toggle_theme)
        top_lay.addWidget(theme_btn)
        settings_btn = QPushButton("⚙")
        settings_btn.setStyleSheet(f"border:0;background:transparent;font-size:18px;padding:0 8px;")
        top_lay.addWidget(settings_btn)
        help_btn = QPushButton("❓")
        help_btn.setStyleSheet(f"border:0;background:transparent;font-size:18px;padding:0 8px;")
        top_lay.addWidget(help_btn)

        # ---- 左侧导航 ----
        self.nav_list = QListWidget()
        for i, (name, _cls) in enumerate(_NAV):
            it = QListWidgetItem(f"{i + 1}.  {name}")
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.nav_list.addItem(it)
        self.nav_list.setFixedWidth(180)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # ---- 主内容区 ----
        self.stack = QStackedWidget()
        self.pages = []
        for _name, cls in _NAV:
            page = cls()
            self.stack.addWidget(page)
            self.pages.append(page)

        # ---- 底栏 ----
        bottom = QWidget()
        bottom.setFixedHeight(64)
        bottom.setStyleSheet(
            f"background:{L['bg_primary']};border-top:1px solid {L['border_default']};"
        )
        bot_lay = QHBoxLayout(bottom)
        bot_lay.setContentsMargins(16, 0, 16, 0)
        self.link_lbl = QLabel("USB-CDC")
        self.link_lbl.setStyleSheet(f"color:{L['text_secondary']};font-size:12px;")
        bot_lay.addWidget(self.link_lbl)
        bot_lay.addStretch(1)
        for name in ["开始", "停止", "导出 CSV"]:
            btn = QPushButton(name)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"background:{L['brand_primary']};color:white;border:0;border-radius:4px;"
                f"padding:0 16px;font-weight:600;margin-left:8px;"
            )
            bot_lay.addWidget(btn)

        # ---- 整体布局 ----
        center = QWidget()
        center_lay = QHBoxLayout(center)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(0)
        center_lay.addWidget(self.nav_list)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{L['border_default']};")
        center_lay.addWidget(sep)
        center_lay.addWidget(self.stack, 1)

        root = QWidget()
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        root_lay.addWidget(topbar)
        root_lay.addWidget(center, 1)
        root_lay.addWidget(bottom)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())

        # 默认选中第一页
        self.nav_list.setCurrentRow(0)

        # 快捷键
        self._install_shortcuts()

    # ---- 导航 ----
    def _on_nav_changed(self, idx: int) -> None:
        if 0 <= idx < self.stack.count():
            self.stack.setCurrentIndex(idx)
            self.statusBar().showMessage(f"页面：{_NAV[idx][0]}", 1500)

    def goto(self, page_index: int) -> None:
        if 0 <= page_index < self.nav_list.count():
            self.nav_list.setCurrentRow(page_index)

    # ---- 快捷键 ----
    def _install_shortcuts(self) -> None:
        for i in range(1, 10):
            act = QAction(self)
            act.setShortcut(QKeySequence(str(i)))
            act.triggered.connect(lambda _checked=False, idx=i - 1: self.goto(idx))
            self.addAction(act)
        for keys, slot in [
            ("Ctrl+O", lambda: self.statusBar().showMessage("打开文件…", 1500)),
            ("Ctrl+S", lambda: self.statusBar().showMessage("开始/停止录制", 1500)),
            ("Ctrl+E", lambda: self.statusBar().showMessage("导出", 1500)),
            ("F1", lambda: self.statusBar().showMessage("帮助（待实现）", 1500)),
            ("F5", lambda: self.statusBar().showMessage("刷新", 1500)),
        ]:
            act = QAction(self)
            act.setShortcut(QKeySequence(keys))
            act.triggered.connect(slot)
            self.addAction(act)

    # ---- 给 AppController 调用的接口 ----
    def get_monitor_page(self) -> PageMonitor:
        return self.pages[0]

    def get_page_index(self, name: str) -> int:
        for i, (n, _cls) in enumerate(_NAV):
            if n == name:
                return i
        raise KeyError(name)

    # ---- 主题切换 ----
    def _toggle_theme(self) -> None:
        new_name = theme.toggle()
        self._restyle()
        for p in self.pages:
            if hasattr(p, "restyle"):
                p.restyle()
            elif hasattr(p, "refresh"):
                p.refresh()
            else:
                p.update()
        self.statusBar().showMessage(f"主题已切换：{new_name}", 1500)

    def _restyle(self) -> None:
        """重建 MainWindow 顶层的 stylesheet（跟随当前主题）。"""
        L = theme.current()
        self.setStyleSheet(
            f"QMainWindow{{background:{L['bg_primary']};}}"
            f"QListWidget{{background:{L['bg_secondary']};border:0;outline:0;color:{L['text_primary']};}}"
            f"QListWidget::item{{padding:12px 16px;color:{L['text_primary']};}}"
            f"QListWidget::item:selected{{background:{L['brand_primary']};color:white;}}"
            f"QStatusBar{{background:{L['bg_secondary']};color:{L['text_secondary']};}}"
        )
