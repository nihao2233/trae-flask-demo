"""通讯适配层。

- DeviceAdapter ABC：所有适配器统一接口
- UsbCdcAdapter：pyserial-asyncio（硬件到位时启用）
- BleAdapter：bleak stub（本轮不启用）
- SimAdapter：Mock，输出符合新协议的字节流
- ConnectionManager：重连 / 心跳 / 指数退避
"""
from .adapter import DeviceAdapter, LinkState
from .models import AdapterInfo, LinkStats
from .sim import SimAdapter

__all__ = [
    "DeviceAdapter", "LinkState",
    "AdapterInfo", "LinkStats",
    "SimAdapter",
]
