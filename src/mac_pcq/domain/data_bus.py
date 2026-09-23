"""DataBus：进程内数据总线。

- 生产侧：asyncio.Queue，由协议层 dispatcher 调用 publish
- 消费侧：Qt Signal（PySide6 启动时挂上），由 UI 订阅
- 也可降级为"纯回调"模式（无 Qt 时跑 smoke test）

设计参考：总体设计 §7.3
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from ..core.logger import get_logger
from ..protocol.spec import (
    TYPE_DATA_ECG, TYPE_DATA_PVDF, TYPE_DATA_RESISTIVE,
    TYPE_HR_RR, TYPE_LEAD_OFF, TYPE_SYS_STATUS, TYPE_DEVICE_INFO,
    TYPE_BATTERY_WARN,
)
from .models import (
    ECGSample, PVDFFrame, ResistiveSample, VitalSigns, SystemStatus, DeviceInfo,
)

_log = get_logger("domain.bus")

try:
    from PySide6.QtCore import QObject, Signal  # type: ignore
    _HAS_QT = True
except ImportError:
    _HAS_QT = False


if _HAS_QT:

    class _BusSignals(QObject):
        ecg_ready = Signal(object)        # ECGSample
        piezo_ready = Signal(object)      # PVDFFrame
        resistive_ready = Signal(object)  # ResistiveSample
        vital_ready = Signal(object)      # VitalSigns
        lead_off = Signal(object)
        system_status = Signal(object)    # SystemStatus
        device_info = Signal(object)      # DeviceInfo
        battery_warn = Signal(object)


class DataBus:
    """asyncio.Queue 生产 + Qt Signal 消费。"""

    def __init__(self, queue_size: int = 1024) -> None:
        self._queue_size = queue_size
        self._queue: asyncio.Queue = None  # type: ignore[assignment]
        self.signals = _BusSignals() if _HAS_QT else None
        self._dropped = 0
        self._callbacks = {
            TYPE_DATA_ECG: [],
            TYPE_DATA_PVDF: [],
            TYPE_DATA_RESISTIVE: [],
            TYPE_HR_RR: [],
            TYPE_LEAD_OFF: [],
            TYPE_SYS_STATUS: [],
            TYPE_DEVICE_INFO: [],
            TYPE_BATTERY_WARN: [],
        }

    def _ensure_queue(self) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=self._queue_size)

    # ---- 生产侧 ----
    async def publish(self, ftype: int, seq: int, model) -> None:
        """协议层调用：把解析后的模型 push 到队列。"""
        self._ensure_queue()
        try:
            self._queue.put_nowait((ftype, seq, model))
        except asyncio.QueueFull:
            self._dropped += 1
            if self._dropped % 100 == 1:
                _log.warning("DataBus queue full, dropped %d", self._dropped)

    def publish_nowait(self, ftype: int, seq: int, model) -> bool:
        self._ensure_queue()
        try:
            self._queue.put_nowait((ftype, seq, model))
            return True
        except asyncio.QueueFull:
            return False

    # ---- 消费侧 ----
    async def consume(self) -> tuple:
        self._ensure_queue()
        return await self._queue.get()

    def qsize(self) -> int:
        self._ensure_queue()
        return self._queue.qsize()

    @property
    def dropped(self) -> int:
        return self._dropped

    # ---- 回放兼容：纯回调订阅 ----
    def subscribe(self, ftype: int, cb: Callable) -> None:
        """无 Qt 时使用：注册同步回调，dispatch 时直接调用。"""
        self._callbacks.setdefault(ftype, []).append(cb)

    def dispatch_sync(self, ftype: int, seq: int, model) -> None:
        for cb in self._callbacks.get(ftype, []):
            try:
                cb(seq, model)
            except Exception:  # noqa: BLE001
                _log.exception("DataBus subscriber failed")

    # ---- 类型转协议模型 → domain 模型 ----
    @staticmethod
    def to_domain(ftype: int, seq: int, model) -> object:
        """把协议层 parsers 解析的模型包一层 ts_us/seq。"""
        ts = getattr(model, "ts_us", None) or 0
        if ftype == TYPE_DATA_ECG:
            return ECGSample(ts_us=ts, ch=model.ch, seq=seq)
        if ftype == TYPE_DATA_PVDF:
            return PVDFFrame(ts_us=ts, ch=model.ch, seq=seq)
        if ftype == TYPE_DATA_RESISTIVE:
            return ResistiveSample(ts_us=ts, r_ohm=list(model.r_ohm), seq=seq)
        if ftype == TYPE_HR_RR:
            return VitalSigns(ts_us=ts, hr_bpm=model.hr_bpm, rr_bpm=model.rr_bpm,
                              quality=model.quality, seq=seq)
        if ftype == TYPE_SYS_STATUS:
            return SystemStatus(
                ts_us=ts,
                charging=model.charging,
                level_pct=model.level_pct,
                vbat_mv=model.vbat_mv,
                v3v3a_mv=model.v3v3a_mv,
                v3v3d_mv=model.v3v3d_mv,
                temp_c=model.temp_c,
                uptime_s=model.uptime_s,
                error_code=model.error_code,
                seq=seq,
            )
        if ftype == TYPE_DEVICE_INFO:
            return DeviceInfo(
                ts_us=ts,
                fw_version=model.fw_version,
                serial=model.serial,
                hw_id=model.hw_id,
                seq=seq,
            )
        return model

    def emit_to_qt(self, ftype: int, seq: int, model) -> None:
        """Qt Signal 派发（在 UI 线程的事件循环里调用）。"""
        if self.signals is None:
            return
        d = self.to_domain(ftype, seq, model)
        if ftype == TYPE_DATA_ECG:
            self.signals.ecg_ready.emit(d)
        elif ftype == TYPE_DATA_PVDF:
            self.signals.piezo_ready.emit(d)
        elif ftype == TYPE_DATA_RESISTIVE:
            self.signals.resistive_ready.emit(d)
        elif ftype == TYPE_HR_RR:
            self.signals.vital_ready.emit(d)
        elif ftype == TYPE_SYS_STATUS:
            self.signals.system_status.emit(d)
        elif ftype == TYPE_DEVICE_INFO:
            self.signals.device_info.emit(d)
        elif ftype == TYPE_BATTERY_WARN:
            self.signals.battery_warn.emit(model)
        elif ftype == TYPE_LEAD_OFF:
            self.signals.lead_off.emit(model)
