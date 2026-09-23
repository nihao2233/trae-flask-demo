"""新增 / 修订测试。"""

import asyncio
import struct

import pytest

from mac_pcq.protocol.codec import Frame
from mac_pcq.protocol.spec import TYPE_SYS_STATUS
from mac_pcq.transport.adapter import LinkState
from mac_pcq.transport.sim import SimAdapter


@pytest.mark.asyncio
async def test_sim_uptime_is_relative():
    """SimAdapter 应返回自 run() 启动以来的相对秒数，而非绝对时间戳。"""
    sim = SimAdapter(vital_period_s=0.05)
    mgr_cm = []
    sim._info.name = "SimMock"  # placeholder
    await sim.connect()
    sim._boot_time = __import__("time").time() - 100  # 假装启动 100 秒
    # 立即读 status 帧
    raw = sim._encode_status()
    f = Frame.decode(raw)
    assert f.type == TYPE_SYS_STATUS
    seq, flags, level, vbat, v3v3a, v3v3d, temp, uptime, err = struct.unpack_from(
        "<IBBHHHBI B", f.payload, 0
    )
    # uptime 应在 95~110 之间（允许 5s 漂移）
    assert 90 <= uptime <= 110, f"uptime={uptime} not relative to boot"
    await sim.disconnect()


def test_theme_toggle_changes_current():
    from mac_pcq.ui import theme
    assert theme.name() == "light"
    new = theme.toggle()
    assert new == "dark"
    assert theme.name() == "dark"
    assert theme.current()["bg_primary"] == "#1A1A1A"
    # 再切回
    new = theme.toggle()
    assert new == "light"
    assert theme.current()["bg_primary"] == "#FFFFFF"


def test_theme_subscribe_notified():
    from mac_pcq.ui import theme
    calls = []
    theme.subscribe(lambda n: calls.append(n))
    theme.set_theme("dark")
    theme.set_theme("light")
    assert calls == ["dark", "light"]
    # 重复不通知
    calls.clear()
    theme.set_theme("light")
    assert calls == []


def test_pages_import():
    """确保 9 个页面都能 import 并构造。"""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from mac_pcq.ui.pages.monitor import PageMonitor
    from mac_pcq.ui.pages.resistive import PageResistive
    from mac_pcq.ui.pages.config import PageConfig
    from mac_pcq.ui.pages.piezo import PagePiezo
    from mac_pcq.ui.pages.vital import PageVital
    from mac_pcq.ui.pages.record import PageRecord
    from mac_pcq.ui.pages.device import PageDevice
    from mac_pcq.ui.pages.upgrade import PageUpgrade
    from mac_pcq.ui.pages.log import PageLog
    for cls in (PageMonitor, PageResistive, PagePiezo, PageVital,
                PageRecord, PageDevice, PageConfig, PageUpgrade, PageLog):
        p = cls()
        assert p is not None


def test_main_window_restyle_no_crash():
    """主题切换不抛异常。"""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from mac_pcq.app import AppController
    from mac_pcq.ui.main_window import MainWindow
    from mac_pcq.ui import theme
    ctrl = AppController()
    win = MainWindow(app_controller=ctrl)
    ctrl.attach_window(win)
    win._toggle_theme()
    win._toggle_theme()
    assert theme.name() == "light"
