"""协议字段常量（与《多模态采集板通讯协议定义》v1 §3.1 / §4 / 附录 A 一致）。

帧格式：
    magic   u16 LE  = 0xAA55
    ver     u8       = 0x01
    type    u8
    seq     u32 LE
    ts_us   u64 LE
    len     u16 LE   (payload 字节数)
    payload [len]
    crc     u16 LE   (CRC16-CCITT，对 [ver+type+seq+ts_us+len+payload] 计算)

HEADER_SIZE = 2 + 1 + 1 + 4 + 8 + 2 = 18 字节
"""

from __future__ import annotations

# 帧头
MAGIC = 0xAA55
PROTO_VER = 0x01
HEADER_SIZE = 18
CRC_SIZE = 2

# -------- type 命名空间（上行 = 设备→上位机，下行 = 上位机→设备） --------
TYPE_DATA_ECG = 0x01        # 上行：4 路 ECG 采样（i24 × 4 = 12B）
TYPE_DATA_PVDF = 0x02       # 上行：2 路 PVDF 采样（i24 × 2 = 6B）
TYPE_DATA_RESISTIVE = 0x03  # 上行：16 路电阻（u16 × 16 = 32B）
TYPE_HR_RR = 0x10           # 上行：心率 + 呼吸率（u16 hr + u16 rr + u8 quality = 5B）
TYPE_LEAD_OFF = 0x11        # 上行：导联脱落状态（u8 lead_off_mask = 1B）
TYPE_SYS_STATUS = 0x20      # 上行：系统状态（14B）
TYPE_DEVICE_INFO = 0x21     # 上行：设备信息（51B）
TYPE_BATTERY_WARN = 0x30    # 上行：电量告警（u8 level_pct + u8 warning_level = 2B）
TYPE_OTA_DATA = 0x40        # 双向：OTA 数据包
TYPE_OTA_ACK = 0x41         # 双向：OTA ACK
TYPE_ACK = 0xF0             # 上行：通用 ACK（u8 acked_type + u32 acked_seq + u8 status = 6B）
TYPE_CMD = 0xF1             # 下行：命令
TYPE_HEARTBEAT = 0xF2       # 双向：心跳（payload 空 / 1B 状态）
TYPE_PARAM_CFG = 0xF3       # 下行：参数配置
TYPE_VERSION_NEGO = 0xFE    # 双向：协议版本协商
TYPE_ERROR = 0xFF           # 上行：错误响应（u32 acked_seq + u8 error_code + u8[16] msg）

# -------- 命令码（type=0xF1） --------
CMD_START_ACQ = 0x01        # 开始采集
CMD_STOP_ACQ = 0x02         # 停止采集
CMD_ONCE_ACQ = 0x03         # 单次采集
CMD_READ_STATUS = 0x10      # 读系统状态
CMD_READ_INFO = 0x11        # 读设备信息
CMD_READ_BAT = 0x12         # 读电量
CMD_READ_LEAD = 0x13        # 读导联
CMD_RESET_MCU = 0x20        # 复位 MCU
CMD_RESET_SENSOR = 0x21     # 复位传感器
CMD_ENTER_OTA = 0x30        # 进入 OTA
CMD_EXIT_OTA = 0x31         # 退出 OTA
CMD_SET_LCD = 0x40          # 设置 LCD
CMD_SET_TIMEOUT = 0x41      # 设置超时
CMD_PROBE = 0xF0            # 探测
CMD_EMERGENCY_STOP = 0xFF   # 紧急停止

# -------- 配置项（type=0xF3） --------
CFG_ECG_FS = 0x01
CFG_PVDF_FS = 0x02
CFG_RES_FS = 0x03
CFG_ECG_PGA = 0x10
CFG_PVDF_PGA = 0x11
CFG_RES_PGA = 0x12
CFG_WIFI_CRED = 0x20
CFG_BT_ENABLE = 0x21
CFG_HR_PERIOD = 0x30
CFG_LCD_BRIGHT = 0x40
CFG_LCD_TIMEOUT = 0x41
CFG_SERIAL = 0x50

# MCU 错误码（type=0xFF 的 payload[1]）
ERR_OK = 0x00
ERR_BAD_CRC = 0x01
ERR_BAD_TYPE = 0x02
ERR_BAD_LEN = 0x03
ERR_BUF_OVERFLOW = 0x10
ERR_NOT_READY = 0x20
ERR_HW_FAULT = 0x30
ERR_OTA_CHECKSUM = 0x40
ERR_OTA_TIMEOUT = 0x41
