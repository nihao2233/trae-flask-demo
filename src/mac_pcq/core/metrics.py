"""性能度量：FPS / 丢帧率 / 延迟直方图。

供调试面板查看（不在 P0 强制范围内，本轮先落接口）。
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Deque, List


@dataclass
class FrameMetrics:
    """渲染帧统计。"""

    target_fps: float = 60.0
    _times: Deque[float] = field(default_factory=lambda: collections.deque(maxlen=120))

    def tick(self) -> None:
        self._times.append(time.perf_counter())

    @property
    def fps(self) -> float:
        if len(self._times) < 2:
            return 0.0
        span = self._times[-1] - self._times[0]
        if span <= 0:
            return 0.0
        return (len(self._times) - 1) / span

    @property
    def dropped_pct(self) -> float:
        if self.target_fps <= 0:
            return 0.0
        return max(0.0, 1.0 - self.fps / self.target_fps) * 100


@dataclass
class LatencyHistogram:
    """端到端延迟直方图（毫秒）。"""

    _samples: Deque[float] = field(default_factory=lambda: collections.deque(maxlen=1024))

    def record(self, ms: float) -> None:
        self._samples.append(ms)

    def snapshot(self) -> dict:
        if not self._samples:
            return {"count": 0}
        s = sorted(self._samples)
        n = len(s)
        return {
            "count": n,
            "min": s[0],
            "p50": s[n // 2],
            "p95": s[int(n * 0.95)],
            "max": s[-1],
        }
