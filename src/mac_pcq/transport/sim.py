"""SimAdapter：Mock 适配器，按新协议持续输出合成数据。

无需硬件，启动后立即产生：
- ECG (type=0x01) ~500 Hz，4 通道
- PVDF (type=0x02) ~500 Hz，2 通道
- Resistive (type=0x03) ~20 Hz，16 通道（4×4 矩阵）
- VitalSigns (type=0x10) ~1 Hz
- SystemStatus (type=0x20) ~1 Hz

每个采样点使用一个独立的 seq。
"""

from __future__ import annotations

import asyncio
import math
import random
import struct
import time
from typing import Optional

from ..core.logger import get_logger
from ..protocol.codec import Frame
from ..protocol.spec import (
    TYPE_DATA_ECG, TYPE_DATA_PVDF, TYPE_DATA_RESISTIVE,
    TYPE_HR_RR, TYPE_SYS_STATUS, TYPE_DEVICE_INFO,
)
from .adapter import DeviceAdapter, LinkState
from .models import AdapterInfo

_log = get_logger("transport.sim")


class SimAdapter(DeviceAdapter):
    """合成数据 Mock 适配器。"""

    def __init__(
        self,
        ecg_fs: int = 500,
        pvdf_fs: int = 500,
        resistive_fs: int = 20,
        vital_period_s: float = 1.0,
    ) -> None:
        super().__init__()
        self._info = AdapterInfo(kind="sim", name="SimMock", port="sim://", baudrate=0)
        self.ecg_fs = ecg_fs
        self.pvdf_fs = pvdf_fs
        self.resistive_fs = resistive_fs
        self.vital_period_s = vital_period_s

        self._t = 0.0
        self._seq = 0
        self._phase = random.random() * math.pi * 2
        self._press_r = 1.5
        self._press_c = 1.5
        self._press_strength = 5.0
        self._boot_time = 0.0  # run() 启动时记录

        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        self._set_state(LinkState.CONNECTING)
        await asyncio.sleep(0.05)
        self._set_state(LinkState.CONNECTED)
        return True

    async def disconnect(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None
        self._set_state(LinkState.DISCONNECTED)

    async def write(self, data: bytes) -> int:
        # Sim 接收命令，更新内部状态即可
        self._stats.tx_bytes += len(data)
        self._stats.tx_frames += 1
        try:
            f = Frame.decode(data)
            _log.debug("sim received type=0x%02X len=%d", f.type, len(f.payload))
        except Exception:  # noqa: BLE001
            pass
        return len(data)

    async def run(self) -> None:
        """主循环：调度各路数据生成。"""
        self._running = True
        self._boot_time = time.time()
        self._set_state(LinkState.STREAMING)

        # 立即发一帧 DeviceInfo
        self._emit_data(self._encode_device_info())
        await asyncio.sleep(0)

        ecg_interval = 1.0 / self.ecg_fs
        pvdf_interval = 1.0 / self.pvdf_fs
        res_interval = 1.0 / self.resistive_fs

        next_ecg = next_pvdf = next_res = next_vital = next_status = asyncio.get_event_loop().time()
        loop = asyncio.get_event_loop()

        try:
            while self._running:
                now = loop.time()
                # ECG
                while next_ecg <= now:
                    self._emit_data(self._encode_ecg())
                    next_ecg += ecg_interval
                # PVDF
                while next_pvdf <= now:
                    self._emit_data(self._encode_pvdf())
                    next_pvdf += pvdf_interval
                # 矩阵
                while next_res <= now:
                    self._emit_data(self._encode_resistive())
                    next_res += res_interval
                # 生命体征 / 系统状态
                if now >= next_vital:
                    self._emit_data(self._encode_vital())
                    next_vital = now + self.vital_period_s
                if now >= next_status:
                    self._emit_data(self._encode_status())
                    next_status = now + self.vital_period_s

                # sleep 到下一个最近事件
                sleep_for = min(next_ecg, next_pvdf, next_res, next_vital, next_status) - now
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                else:
                    await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        finally:
            self._set_state(LinkState.CONNECTED)

    # ---- payload 编码 ----
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _now_us(self) -> int:
        return time.time_ns() // 1000

    def _encode_ecg(self) -> bytes:
        self._t += 1.0 / self.ecg_fs
        # 4 路合成：主峰 + T 波 + 漂移 + 噪声
        ch = []
        for c in range(4):
            t = self._t - 0.005 * c
            p1 = math.exp(-((t % 1.0 - 0.15) ** 2) / 0.0015)
            p2 = 0.25 * math.exp(-((t % 1.0 - 0.55) ** 2) / 0.008)
            bl = 0.05 * math.sin(2 * math.pi * 0.1 * t)
            noise = random.gauss(0, 0.015)
            gain = 1.0 + 0.05 * c
            ch.append(int((p1 + p2 + bl + noise) * gain * 1000))
        payload = struct.pack("<I", self._next_seq()) + struct.pack("<4i", *ch)
        return Frame(
            type=TYPE_DATA_ECG,
            seq=self._seq,
            ts_us=self._now_us(),
            payload=payload,
        ).encode()

    def _encode_pvdf(self) -> bytes:
        self._t += 1.0 / self.pvdf_fs
        a = int(2.0 * math.sin(2 * math.pi * 0.5 * self._t + 0) * 1000 + random.gauss(0, 0.1) * 1000)
        b = int(1.5 * math.sin(2 * math.pi * 0.8 * self._t + 1.0) * 1000 + random.gauss(0, 0.1) * 1000)
        payload = struct.pack("<I", self._next_seq()) + struct.pack("<2i", a, b)
        return Frame(
            type=TYPE_DATA_PVDF,
            seq=self._seq,
            ts_us=self._now_us(),
            payload=payload,
        ).encode()

    def _encode_resistive(self) -> bytes:
        strength = 5.0 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.2 * self._t))
        r = []
        for row in range(4):
            for col in range(4):
                d = math.hypot(row - self._press_r, col - self._press_c)
                base = 30.0
                drop = strength * math.exp(-(d ** 2) / 2.0)
                r.append(max(0, int((base - drop + random.gauss(0, 0.3)) * 1000)))  # Ω
        payload = struct.pack("<I", self._next_seq()) + struct.pack("<16H", *r)
        return Frame(
            type=TYPE_DATA_RESISTIVE,
            seq=self._seq,
            ts_us=self._now_us(),
            payload=payload,
        ).encode()

    def _encode_vital(self) -> bytes:
        hr = 72 + random.randint(-2, 2)
        rr = 18 + random.randint(-1, 1)
        payload = struct.pack("<IHHB", self._next_seq(), hr, rr, 95)
        return Frame(
            type=TYPE_HR_RR,
            seq=self._seq,
            ts_us=self._now_us(),
            payload=payload,
        ).encode()

    def _encode_status(self) -> bytes:
        uptime = int(time.time() - self._boot_time) if self._boot_time > 0 else 0
        # 慢漂移：电量缓慢下降、电压 / 温度微抖动
        battery = max(20, 95 - uptime // 30)  # 每 30s 掉 1%
        voltage = 3850 + int(20 * math.sin(self._t * 0.05))
        temp = 35 + int(2 * math.sin(self._t * 0.1))
        payload = struct.pack(
            "<IBBHHHBI B",
            self._next_seq(),
            0x01, battery, voltage, 3300, 3300,
            temp, uptime, 0,
        )
        return Frame(
            type=TYPE_SYS_STATUS,
            seq=self._seq,
            ts_us=self._now_us(),
            payload=payload,
        ).encode()

    def _encode_device_info(self) -> bytes:
        payload = struct.pack("<I", self._next_seq()) + struct.pack("<BBB", 1, 0, 0)
        payload += b"SN-SIM-0001\x00" + b"\x00" * 4   # 16B serial
        payload += b"HW-REV-A\x00" + b"\x00" * 23      # 32B hw_id
        return Frame(
            type=TYPE_DEVICE_INFO,
            seq=self._seq,
            ts_us=self._now_us(),
            payload=payload,
        ).encode()
