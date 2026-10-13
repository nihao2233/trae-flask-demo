"""Windows 平台工具：串口枚举等。"""

from __future__ import annotations

import os
from typing import List


def list_serial_ports() -> List[str]:
    """列出可用串口。

    优先用 pyserial.tools.list_ports；缺失时返回空。
    """
    try:
        from serial.tools import list_ports  # type: ignore
        return sorted(p.device for p in list_ports.comports())
    except ImportError:
        return []


def is_admin() -> bool:
    if os.name != "nt":
        return os.geteuid() == 0
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False
