"""DeviceAdapter ABC + LinkState 枚举。

所有具体适配器（USB / BLE / Sim）必须实现以下接口。
"""

from __future__ import annotations

import abc
import asyncio
from enum import Enum
from typing import Callable, Optional

from .models import AdapterInfo, LinkStats


class LinkState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    UPGRADING = "upgrading"
    ERROR = "error"


class DeviceAdapter(abc.ABC):
    """通讯适配器抽象基类。

    状态机：
        DISCONNECTED → CONNECTING → CONNECTED → STREAMING
                                        ↓
                                    UPGRADING / ERROR
    """

    def __init__(self) -> None:
        self._state: LinkState = LinkState.DISCONNECTED
        self._info: AdapterInfo = AdapterInfo()
        self._stats: LinkStats = LinkStats()
        self._state_cb: Optional[Callable[[LinkState], None]] = None
        self._rx_cb: Optional[Callable[[bytes], None]] = None

    # ---- 状态 ----
    def get_state(self) -> LinkState:
        return self._state

    def get_info(self) -> AdapterInfo:
        return self._info

    def get_stats(self) -> LinkStats:
        return self._stats

    def _set_state(self, s: LinkState) -> None:
        if s != self._state:
            self._state = s
            if self._state_cb:
                try:
                    self._state_cb(s)
                except Exception:  # noqa: BLE001
                    pass

    # ---- 回调注册 ----
    def on_state_changed(self, cb: Callable[[LinkState], None]) -> None:
        self._state_cb = cb

    def on_data(self, cb: Callable[[bytes], None]) -> None:
        self._rx_cb = cb

    # ---- 异步 IO ----
    @abc.abstractmethod
    async def connect(self) -> bool: ...

    @abc.abstractmethod
    async def disconnect(self) -> None: ...

    @abc.abstractmethod
    async def write(self, data: bytes) -> int: ...

    @abc.abstractmethod
    async def run(self) -> None:
        """后台读循环：持续调用 _emit_data(bytes) 直到 disconnect。"""

    # ---- 内部辅助 ----
    def _emit_data(self, data: bytes) -> None:
        self._stats.rx_bytes += len(data)
        if self._rx_cb:
            try:
                self._rx_cb(data)
            except Exception:  # noqa: BLE001
                pass
