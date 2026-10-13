"""BleAdapter：基于 bleak 的 BLE 适配器 stub（硬件到位后启用）。

BLE 仅传输控制帧（见《通讯协议定义》§3.2 强制约束），
数据流仍走 USB CDC 或 Wi-Fi。本轮不实现。
"""

from __future__ import annotations

from ..core.logger import get_logger
from .adapter import DeviceAdapter, LinkState
from .models import AdapterInfo

_log = get_logger("transport.ble")


class BleAdapter(DeviceAdapter):
    def __init__(self, device_name: str | None = None, passkey: str | None = None) -> None:
        super().__init__()
        self._info = AdapterInfo(
            kind="ble",
            name=device_name or "",
            port=device_name or "",
            extra={"passkey": passkey or ""},
        )

    async def connect(self) -> bool:
        _log.warning("BleAdapter not implemented yet (waiting for hardware)")
        self._set_state(LinkState.ERROR)
        return False

    async def disconnect(self) -> None:
        self._set_state(LinkState.DISCONNECTED)

    async def write(self, data: bytes) -> int:
        return 0

    async def run(self) -> None:
        return None
