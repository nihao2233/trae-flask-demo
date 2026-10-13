"""ConnectionManager：包装 DeviceAdapter，提供：
- 自动重连（指数退避 1s → 2s → 4s → 8s → 16s → 30s 上限）
- 心跳循环（1 Hz）
- 接收字节流分发
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from ..core.logger import get_logger
from .adapter import DeviceAdapter, LinkState

_log = get_logger("transport.manager")


class ConnectionManager:
    """管理一个 DeviceAdapter 的生命周期。"""

    BACKOFF_STEPS = [1, 2, 4, 8, 16, 30]   # 秒

    def __init__(
        self,
        adapter: DeviceAdapter,
        on_data: Callable[[bytes], None],
        on_state: Optional[Callable[[LinkState], None]] = None,
        heartbeat_period_s: float = 1.0,
    ) -> None:
        self.adapter = adapter
        self._on_data = on_data
        self._on_state = on_state
        self.heartbeat_period_s = heartbeat_period_s
        self._run_task: Optional[asyncio.Task] = None
        self._hb_task: Optional[asyncio.Task] = None
        self._stop_evt = asyncio.Event()

    async def start(self) -> None:
        ok = await self.adapter.connect()
        if not ok:
            self._schedule_reconnect()
            return
        self._stop_evt.clear()
        # 把适配器数据直接转给 dispatcher
        self.adapter.on_data(self._on_data)
        if self._on_state:
            self.adapter.on_state_changed(self._on_state)
        # 启动后台 run + 心跳
        self._run_task = asyncio.create_task(self.adapter.run(), name="adapter.run")
        self._hb_task = asyncio.create_task(self._heartbeat_loop(), name="adapter.heartbeat")

    async def stop(self) -> None:
        self._stop_evt.set()
        for t in (self._hb_task, self._run_task):
            if t:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        await self.adapter.disconnect()
        self._run_task = None
        self._hb_task = None

    def _schedule_reconnect(self) -> None:
        asyncio.create_task(self._reconnect_loop(), name="adapter.reconnect")

    async def _reconnect_loop(self) -> None:
        for delay in self.BACKOFF_STEPS:
            if self._stop_evt.is_set():
                return
            _log.warning("reconnect in %ds", delay)
            await asyncio.sleep(delay)
            if await self.adapter.connect():
                _log.info("reconnected")
                self.adapter._stats.reconnects += 1
                # 重新启动 run
                self._run_task = asyncio.create_task(self.adapter.run(), name="adapter.run")
                return
        _log.error("reconnect failed after all attempts")

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._stop_evt.is_set():
                # 这里仅做"节拍"，真实心跳帧可由业务层通过 self.adapter.write 发送
                await asyncio.sleep(self.heartbeat_period_s)
        except asyncio.CancelledError:
            return
