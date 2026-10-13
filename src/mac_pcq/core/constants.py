"""全局常量。

集中放置版本号、默认采样率 / 窗口大小 / 数据目录等全局只读值。
"""

from __future__ import annotations

APP_NAME = "多模态采集板上位机"
APP_VERSION = "0.1.0"

# 默认采样率（Hz）
DEFAULT_ECG_FS = 500
DEFAULT_PVDF_FS = 500
DEFAULT_RESISTIVE_FS = 50  # 压阻矩阵本身不需要高采样

# 默认 UI 显示窗口（秒）
DEFAULT_WINDOW_S = 5.0

# 环形缓冲时长（秒）—— 满足 60fps 渲染 + 10s 历史
RING_BUFFER_S = 10.0

# 心率合理范围（BPM）
HR_MIN = 30
HR_MAX = 220

# 呼吸率合理范围（BPM）
RR_MIN = 5
RR_MAX = 60

# 心电 Y 轴范围（mV）
ECG_Y_RANGE_MV = 1.0

# 压电 Y 轴范围（mV）
PVDF_Y_RANGE_MV = 10.0

# 矩阵色阶默认范围
RES_MIN_KOHM = 10.0
RES_MAX_KOHM = 500.0
PRESS_MIN_N = 100.0
PRESS_MAX_N = 5000.0

# 协议相关（与 protocol/spec.py 保持一致）
HEADER_SIZE = 18
CRC_SIZE = 2

# 默认串口参数
DEFAULT_BAUDRATE = 115200

# 数据目录
import os
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "data",
)
