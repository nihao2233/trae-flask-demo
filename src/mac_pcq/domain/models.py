"""domain 层数据模型（与 protocol.parsers 解耦）。

parsers 负责从 payload 字节流解析；这里负责给上层（UI / session / signal_proc）
使用的"业务友好"模型，附 ts_us、来源等元数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ECGSample:
    """单个 ECG 采样点。"""

    ts_us: int
    ch: Tuple[int, int, int, int]   # 4 路 i24 ADC
    seq: int = 0


@dataclass
class PVDFFrame:
    """单个 PVDF 采样点。"""

    ts_us: int
    ch: Tuple[int, int]
    seq: int = 0


@dataclass
class ResistiveSample:
    """4×4 电阻矩阵采样。"""

    ts_us: int
    r_ohm: List[int]    # 16 个 Ω 值
    seq: int = 0


@dataclass
class VitalSigns:
    ts_us: int
    hr_bpm: int
    rr_bpm: int
    quality: int
    seq: int = 0


@dataclass
class SystemStatus:
    ts_us: int
    charging: bool
    level_pct: int
    vbat_mv: int
    v3v3a_mv: int
    v3v3d_mv: int
    temp_c: int
    uptime_s: int
    error_code: int
    seq: int = 0


@dataclass
class DeviceInfo:
    ts_us: int
    fw_version: Tuple[int, int, int]
    serial: str
    hw_id: str
    seq: int = 0
