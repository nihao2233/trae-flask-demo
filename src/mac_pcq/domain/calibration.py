"""电阻 ↔ 压力换算。

P0 实现分段线性（参见 UI 设计 §6.2.4）：
  R < 10 kΩ → P = R × a₁
  R ≥ 10 kΩ → P = R × a₂ + b
并支持"两点标定"自动求 a, b。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CalibrationConfig:
    a1: float = 0.01
    a2: float = 0.005
    b: float = 25.0
    breakpoint_kohm: float = 10.0


class Calibration:
    @staticmethod
    def resistance_to_pressure(r_ohm: float, cfg: CalibrationConfig) -> float:
        r_kohm = r_ohm / 1000.0
        if r_kohm < cfg.breakpoint_kohm:
            return cfg.a1 * r_kohm
        return cfg.a2 * r_kohm + cfg.b

    @staticmethod
    def calibrate_two_point(r1: float, p1: float, r2: float, p2: float) -> tuple[float, float]:
        """两点标定：返回 (a, b) 满足 P = a·R + b。

        假设两点都在 [breakpoint_kohm, +∞) 区间。
        """
        if r2 == r1:
            raise ValueError("r1 and r2 must differ")
        a = (p2 - p1) / (r2 - r1)
        b = p1 - a * r1
        return a, b
