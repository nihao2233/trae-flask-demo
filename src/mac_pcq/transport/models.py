"""通讯层数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AdapterInfo:
    """适配器身份信息。"""

    kind: str = ""            # "usb" / "ble" / "sim"
    name: str = ""            # "COM3" / "DeviceName" / "SimMock"
    port: str = ""            # 同 name
    baudrate: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class LinkStats:
    """链路统计（debug 面板用）。"""

    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_frames: int = 0
    tx_frames: int = 0
    crc_errors: int = 0
    reconnects: int = 0
    last_rx_us: int = 0
    last_tx_us: int = 0
