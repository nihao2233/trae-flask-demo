"""UsbCdcAdapter：基于 pyserial-asyncio 的 USB CDC 串口适配器（硬件到位后启用）。

本轮 stub：实现完整接口，但 connect 直接返回 False 并打日志。
P1 后续：在硬件到位后实现 connect / run / write。
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..core.logger import get_logger
from .adapter import DeviceAdapter, LinkState
from .models import AdapterInfo

_log = get_logger("transport.usb_cdc")


class UsbCdcAdapter(DeviceAdapter):
    def __init__(self, port: str, baudrate: int = 115200) -> None:
        super().__init__()
        self._info = AdapterInfo(kind="usb", name=port, port=port, baudrate=baudrate)
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> bool:
        self._set_state(LinkState.CONNECTING)
        try:
            import serial_asyncio  # noqa: WPS433  # type: ignore
        except ImportError:
            _log.error("pyserial-asyncio not installed")
            self._set_state(LinkState.ERROR)
            return False
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._info.port,
                baudrate=self._info.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
            )
        except Exception as exc:  # noqa: BLE001
            _log.error("USB CDC connect failed: %s", exc)
            self._set_state(LinkState.ERROR)
            return False
        self._set_state(LinkState.CONNECTED)
        return True

    async def disconnect(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        self._writer = None
        self._reader = None
        self._set_state(LinkState.DISCONNECTED)

    async def write(self, data: bytes) -> int:
        if not self._writer:
            return 0
        self._writer.write(data)
        await self._writer.drain()
        self._stats.tx_bytes += len(data)
        self._stats.tx_frames += 1
        return len(data)

    async def run(self) -> None:
        if not self._reader:
            self._set_state(LinkState.ERROR)
            return
        self._set_state(LinkState.STREAMING)
        try:
            while True:
                chunk = await self._reader.read(4096)
                if not chunk:
                    break
                self._emit_data(chunk)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _log.error("USB CDC read error: %s", exc)
        finally:
            self._set_state(LinkState.CONNECTED)
