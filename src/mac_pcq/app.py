"""AppController：装配 core / transport / protocol / domain / ui。

- 持有 DataBus / SessionService / ConnectionManager
- 启动 SimAdapter（默认），把字节流喂给 FrameDispatcher
- dispatcher → DataBus → UI Signal（qt）+ 同步回调
- UI 状态同步：LinkIndicator / StatusBadge
"""

from __future__ import annotations

import asyncio
from typing import Optional

from .core.config import Config
from .core.error_handler import UserFacingError, install_global_hook
from .core.logger import get_logger, setup_logging
from .domain.data_bus import DataBus
from .domain.session import SessionService
from .protocol.dispatcher import FrameDispatcher
from .transport.adapter import LinkState
from .transport.manager import ConnectionManager
from .transport.sim import SimAdapter

_log = get_logger("app")


class AppController:
    """应用主控。"""

    def __init__(self, config: Optional[Config] = None) -> None:
        setup_logging(level="INFO")
        install_global_hook()
        self.config = config or Config()
        self.bus = DataBus(queue_size=4096)
        self.session = SessionService()
        self.adapter = SimAdapter()  # 默认 Mock
        self.dispatcher = FrameDispatcher(on_payload=self._on_payload)
        self.conn: Optional[ConnectionManager] = None
        self._window = None

        # 业务层 → UI 的状态同步
        self._ui_state_cbs = []
        self._ui_session_cbs = []
        self.session.on_state_changed(self._notify_session_state)

    # ---- UI 接入 ----
    def attach_window(self, window) -> None:
        self._window = window
        # DataBus Qt Signal → PageMonitor
        monitor = window.get_monitor_page()
        if self.bus.signals is not None:
            self.bus.signals.ecg_ready.connect(monitor.on_ecg)
            self.bus.signals.piezo_ready.connect(monitor.on_piezo)
            self.bus.signals.resistive_ready.connect(monitor.on_resistive)
            self.bus.signals.vital_ready.connect(monitor.on_vital)
            self.bus.signals.system_status.connect(monitor.on_system_status)
        # 链路状态
        if window.link_ind is not None:
            self._ui_state_cbs.append(window.link_ind.set_state)
            self._ui_session_cbs.append(window.status_badge.set_state)
        # 把 send_cmd 注入 PageConfig
        idx = window.get_page_index("参数配置")
        page = window.pages[idx]
        if hasattr(page, "set_send_cmd"):
            async def _send(frame_bytes: bytes) -> None:
                if self.adapter is not None:
                    await self.adapter.write(frame_bytes)
            page.set_send_cmd(_send)

    # ---- 异步任务 ----
    async def start(self) -> None:
        """启动 adapter + 接收循环 + dispatcher 消费者。"""
        self.conn = ConnectionManager(
            self.adapter,
            on_data=self.dispatcher.feed,
            on_state=self._notify_link_state,
        )
        await self.conn.start()
        # 启动 DataBus 消费者协程
        self._consumer_task = asyncio.create_task(self._consume_loop(), name="bus.consumer")

    async def stop(self) -> None:
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self.conn:
            await self.conn.stop()

    # ---- 内部 ----
    def _on_payload(self, ftype: int, seq: int, model) -> None:
        """dispatcher → DataBus（Qt Signal 派发 + 同步订阅）。"""
        # 同步回调（测试 / 业务订阅）
        self.bus.dispatch_sync(ftype, seq, model)
        # Qt Signal（UI）
        self.bus.emit_to_qt(ftype, seq, model)

    def _notify_link_state(self, s: LinkState) -> None:
        _log.info("link state -> %s", s.value)
        for cb in self._ui_state_cbs:
            try:
                cb(s)
            except Exception:  # noqa: BLE001
                pass

    def _notify_session_state(self, s) -> None:
        _log.info("session state -> %s", s.value)
        for cb in self._ui_session_cbs:
            try:
                cb(s)
            except Exception:  # noqa: BLE001
                pass

    async def _consume_loop(self) -> None:
        """从 DataBus 拉队列（额外通道；Qt Signal 已经在 emit_to_qt 里发到 UI）。"""
        try:
            while True:
                _ftype, _seq, _model = await self.bus.consume()
                # 占位：UI 已经通过 Qt Signal 拿到；这里可以再做落盘 / 分析
        except asyncio.CancelledError:
            return
