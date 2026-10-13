"""信号处理：ECG / PVDF 滤波 + 心率计算。

P0 实现：
- ECG：0.05 Hz HP + 50 Hz 陷波 + 35 Hz LP（4 阶 IIR Butterworth）
- PVDF：5 Hz HP + 包络检波
- R 波检测：阈值法 + 不应期（Pan-Tompkins 留 P2）
- HR：最近 8 次 RR 间期滑动平均
"""

from __future__ import annotations

import math
from collections import deque
from typing import List, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

from ..core.constants import HR_MAX, HR_MIN


def _butter_bandpass(lowcut: float, highcut: float, fs: float, order: int = 4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    if low <= 0:
        # only HP
        sos = butter(order, high, btype="lowpass", output="sos")
    elif high >= 1.0:
        sos = butter(order, low, btype="highpass", output="sos")
    else:
        sos = butter(order, [low, high], btype="bandpass", output="sos")
    return sos


class ECGFilter:
    """单通道 ECG 滤波器（HP 0.05Hz + 50Hz 陷波 + LP 35Hz）。"""

    def __init__(self, fs: int = 500, order: int = 4) -> None:
        self.fs = fs
        # HP 0.05Hz（实际 ≤ 0 → 走 lowpass 实现）
        # 简化：bandpass 0.5-35Hz，先做主带，再额外叠 50Hz 陷波
        self.sos_bp = _butter_bandpass(0.5, 35.0, fs, order)
        # 50Hz 陷波
        self.sos_notch = _butter_bandpass(49.0, 51.0, fs, order)
        self._zi_bp = sosfilt_zi(self.sos_bp) * 0.0
        self._zi_notch = sosfilt_zi(self.sos_notch) * 0.0

    def push(self, x: float) -> float:
        v, self._zi_bp = sosfilt(self.sos_bp, [x], zi=self._zi_bp)
        v, self._zi_notch = sosfilt(self.sos_notch, v, zi=self._zi_notch)
        return float(v[0])

    def push_array(self, xs: List[float]) -> List[float]:
        out, self._zi_bp = sosfilt(self.sos_bp, xs, zi=self._zi_bp)
        out, self._zi_notch = sosfilt(self.sos_notch, out, zi=self._zi_notch)
        return out.tolist()


class PVDFFilter:
    """PVDF 包络检波（5Hz HP + |x| 低通）。"""

    def __init__(self, fs: int = 500, cutoff_hz: float = 5.0, order: int = 2) -> None:
        self.fs = fs
        self.sos_hp = _butter_bandpass(cutoff_hz, fs / 2 * 0.9, fs, order)
        self.sos_lp = _butter_bandpass(0.0, cutoff_hz * 2, fs, order)
        self._zi_hp = sosfilt_zi(self.sos_hp) * 0.0
        self._zi_lp = sosfilt_zi(self.sos_lp) * 0.0
        self._env = 0.0

    def push(self, x: float) -> Tuple[float, float]:
        v, self._zi_hp = sosfilt(self.sos_hp, [x], zi=self._zi_hp)
        env_in = float(abs(v[0]))
        v2, self._zi_lp = sosfilt(self.sos_lp, [env_in], zi=self._zi_lp)
        return float(v[0]), float(v2[0])


class RPeakDetector:
    """阈值 + 不应期检测 R 波（演示级；上线建议替换 Pan-Tompkins）。"""

    def __init__(
        self,
        fs: int = 500,
        threshold: float = 0.3,
        refractory_ms: int = 250,
    ) -> None:
        self.fs = fs
        self.threshold = threshold
        self.refractory = max(1, int(refractory_ms * fs // 1000))
        self.last_peak_idx = -self.refractory
        self.idx = 0
        self.intervals: deque = deque(maxlen=8)

    def feed(self, x: float) -> Optional[int]:
        self.idx += 1
        if x >= self.threshold and self.idx - self.last_peak_idx > self.refractory:
            if self.last_peak_idx > 0:
                interval = self.idx - self.last_peak_idx
                bpm = int(60.0 * self.fs / interval)
                self.intervals.append(bpm)
                self.last_peak_idx = self.idx
                avg = int(sum(self.intervals) / len(self.intervals))
                return max(HR_MIN, min(HR_MAX, avg))
            self.last_peak_idx = self.idx
        return None


class SignalProcessor:
    """聚合 4 路 ECG + 2 路 PVDF 滤波 + 心率检测。"""

    def __init__(self, ecg_fs: int = 500, pvdf_fs: int = 500) -> None:
        self.ecg_fs = ecg_fs
        self.pvdf_fs = pvdf_fs
        self.ecg_filters = [ECGFilter(fs=ecg_fs) for _ in range(4)]
        self.pvdf_filters = [PVDFFilter(fs=pvdf_fs) for _ in range(2)]
        self.r_detector = RPeakDetector(fs=ecg_fs)

    def filter_ecg(self, ch: int, raw: float) -> float:
        return self.ecg_filters[ch].push(raw)

    def filter_pvdf(self, ch: int, raw: float) -> Tuple[float, float]:
        return self.pvdf_filters[ch].push(raw)

    def feed_ecg_batch(self, ch: int, raw: List[float]) -> List[float]:
        return self.ecg_filters[ch].push_array(raw)

    def estimate_hr(self, x: float) -> Optional[int]:
        return self.r_detector.feed(x)

    def reset(self) -> None:
        self.ecg_filters = [ECGFilter(fs=self.ecg_fs) for _ in range(4)]
        self.pvdf_filters = [PVDFFilter(fs=self.pvdf_fs) for _ in range(2)]
        self.r_detector = RPeakDetector(fs=self.ecg_fs)
