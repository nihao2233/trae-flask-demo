"""payload 解析：type → 模型。

每个 parser 严格按协议附录 A 的字段定义；未知 type 抛 UnknownTypeError。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Tuple

from .errors import UnknownTypeError
from .spec import (
    TYPE_DATA_ECG, TYPE_DATA_PVDF, TYPE_DATA_RESISTIVE,
    TYPE_HR_RR, TYPE_LEAD_OFF, TYPE_SYS_STATUS, TYPE_DEVICE_INFO,
    TYPE_BATTERY_WARN, TYPE_ACK, TYPE_ERROR,
)


@dataclass
class ECGFrame:
    seq: int
    ch: Tuple[int, int, int, int]   # i24 × 4

    @classmethod
    def from_payload(cls, payload: bytes) -> "ECGFrame":
        # 字段：seq(u32) + 4 × i24
        if len(payload) < 4 + 12:
            raise ValueError(f"ECGFrame payload too short: {len(payload)}")
        seq = struct.unpack_from("<I", payload, 0)[0]
        ch = struct.unpack_from("<4i", payload, 4)
        return cls(seq=seq, ch=tuple(ch))


@dataclass
class PVDFFrame:
    seq: int
    ch: Tuple[int, int]              # i24 × 2

    @classmethod
    def from_payload(cls, payload: bytes) -> "PVDFFrame":
        if len(payload) < 4 + 6:
            raise ValueError(f"PVDFFrame payload too short: {len(payload)}")
        seq = struct.unpack_from("<I", payload, 0)[0]
        ch = struct.unpack_from("<2i", payload, 4)
        return cls(seq=seq, ch=tuple(ch))


@dataclass
class ResistiveFrame:
    seq: int
    r_ohm: Tuple[int, ...]           # u16 × 16

    @classmethod
    def from_payload(cls, payload: bytes) -> "ResistiveFrame":
        if len(payload) < 4 + 32:
            raise ValueError(f"ResistiveFrame payload too short: {len(payload)}")
        seq = struct.unpack_from("<I", payload, 0)[0]
        r = struct.unpack_from("<16H", payload, 4)
        return cls(seq=seq, r_ohm=tuple(r))


@dataclass
class VitalSigns:
    seq: int
    hr_bpm: int
    rr_bpm: int
    quality: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "VitalSigns":
        if len(payload) < 4 + 5:
            raise ValueError(f"VitalSigns payload too short: {len(payload)}")
        seq, hr, rr, quality = struct.unpack_from("<IHHB", payload, 0)
        return cls(seq=seq, hr_bpm=hr, rr_bpm=rr, quality=quality)


@dataclass
class LeadOffStatus:
    seq: int
    mask: int   # u8：bit i 表示通道 i 脱落

    @classmethod
    def from_payload(cls, payload: bytes) -> "LeadOffStatus":
        if len(payload) < 4 + 1:
            raise ValueError(f"LeadOffStatus payload too short: {len(payload)}")
        seq, mask = struct.unpack_from("<IB", payload, 0)
        return cls(seq=seq, mask=mask)


@dataclass
class SystemStatus:
    seq: int
    charging: bool
    level_pct: int
    vbat_mv: int
    v3v3a_mv: int
    v3v3d_mv: int
    temp_c: int
    uptime_s: int
    error_code: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "SystemStatus":
        # seq(u32) + flags(u8) + level(u8) + vbat(u16) + 3v3a(u16) + 3v3d(u16)
        # + temp(u8) + uptime(u32) + error(u8)
        if len(payload) < 4 + 1 + 1 + 2 + 2 + 2 + 1 + 4 + 1:
            raise ValueError(f"SystemStatus payload too short: {len(payload)}")
        (seq, flags, level, vbat, v3v3a, v3v3d, temp, uptime, err) = struct.unpack_from(
            "<IBBH H H B I B", payload, 0
        )
        return cls(
            seq=seq,
            charging=bool(flags & 0x01),
            level_pct=level,
            vbat_mv=vbat,
            v3v3a_mv=v3v3a,
            v3v3d_mv=v3v3d,
            temp_c=temp,
            uptime_s=uptime,
            error_code=err,
        )


@dataclass
class DeviceInfo:
    seq: int
    fw_version: Tuple[int, int, int]   # major.minor.patch
    serial: str
    hw_id: str

    @classmethod
    def from_payload(cls, payload: bytes) -> "DeviceInfo":
        if len(payload) < 4 + 3 + 16 + 32:
            raise ValueError(f"DeviceInfo payload too short: {len(payload)}")
        seq, major, minor, patch = struct.unpack_from("<IBBB", payload, 0)
        serial_bytes = payload[7:23]
        serial = serial_bytes.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        hw_bytes = payload[23:55]
        hw_id = hw_bytes.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        return cls(
            seq=seq,
            fw_version=(major, minor, patch),
            serial=serial,
            hw_id=hw_id,
        )


@dataclass
class BatteryWarning:
    seq: int
    level_pct: int
    warning_level: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "BatteryWarning":
        if len(payload) < 4 + 2:
            raise ValueError(f"BatteryWarning payload too short: {len(payload)}")
        seq, level, warn = struct.unpack_from("<IBB", payload, 0)
        return cls(seq=seq, level_pct=level, warning_level=warn)


@dataclass
class AckFrame:
    acked_type: int
    acked_seq: int
    status: int

    @classmethod
    def from_payload(cls, payload: bytes) -> "AckFrame":
        if len(payload) < 1 + 4 + 1:
            raise ValueError(f"AckFrame payload too short: {len(payload)}")
        atype, aseq, status = struct.unpack_from("<BIB", payload, 0)
        return cls(acked_type=atype, acked_seq=aseq, status=status)


@dataclass
class ErrorFrame:
    acked_seq: int
    error_code: int
    msg: str

    @classmethod
    def from_payload(cls, payload: bytes) -> "ErrorFrame":
        if len(payload) < 4 + 1:
            raise ValueError(f"ErrorFrame payload too short: {len(payload)}")
        seq, code = struct.unpack_from("<IB", payload, 0)
        msg = payload[5:21].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        return cls(acked_seq=seq, error_code=code, msg=msg)


# 公共入口
PARSERS = {
    TYPE_DATA_ECG: ECGFrame,
    TYPE_DATA_PVDF: PVDFFrame,
    TYPE_DATA_RESISTIVE: ResistiveFrame,
    TYPE_HR_RR: VitalSigns,
    TYPE_LEAD_OFF: LeadOffStatus,
    TYPE_SYS_STATUS: SystemStatus,
    TYPE_DEVICE_INFO: DeviceInfo,
    TYPE_BATTERY_WARN: BatteryWarning,
    TYPE_ACK: AckFrame,
    TYPE_ERROR: ErrorFrame,
}


def parse(ftype: int, payload: bytes, seq: int = 0):
    """按 type 选择 parser，返回对应模型。

    顶层还会在 dispatcher 里包一层 `(seq, parsed_model)`。
    """
    cls = PARSERS.get(ftype)
    if cls is None:
        raise UnknownTypeError(ftype)
    return cls.from_payload(payload)
