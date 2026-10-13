"""命令构造器：把业务动作打包成 Frame（type=0xF1 / 0xF3 / 0xF2）。"""

from __future__ import annotations

import struct
from typing import Optional

from .codec import Frame
from .spec import (
    TYPE_CMD, TYPE_PARAM_CFG, TYPE_HEARTBEAT, TYPE_ACK,
    CMD_START_ACQ, CMD_STOP_ACQ, CMD_ONCE_ACQ,
    CMD_READ_STATUS, CMD_READ_INFO, CMD_READ_BAT, CMD_READ_LEAD,
    CMD_RESET_MCU, CMD_RESET_SENSOR,
    CMD_ENTER_OTA, CMD_EXIT_OTA,
    CMD_SET_LCD, CMD_SET_TIMEOUT, CMD_PROBE, CMD_EMERGENCY_STOP,
    CFG_ECG_FS, CFG_PVDF_FS, CFG_RES_FS,
    CFG_ECG_PGA, CFG_PVDF_PGA, CFG_RES_PGA,
    CFG_HR_PERIOD, CFG_LCD_BRIGHT, CFG_LCD_TIMEOUT,
)


def _cmd_frame(cmd: int, mode: int = 0, seq: int = 0) -> Frame:
    """type=0xF1 命令帧，payload = cmd(u8) + mode(u8)。"""
    return Frame(type=TYPE_CMD, seq=seq, payload=struct.pack("<BB", cmd, mode))


def _cfg_frame(cfg_id: int, value_u32: int, seq: int = 0) -> Frame:
    """type=0xF3 配置帧，payload = cfg_id(u8) + value(u32 LE)。"""
    return Frame(type=TYPE_PARAM_CFG, seq=seq, payload=struct.pack("<BI", cfg_id, value_u32))


class CommandBuilder:
    """所有下行命令的静态工厂集合。"""

    # 采集控制
    @staticmethod
    def start_acq(mode: int = 0, seq: int = 0) -> bytes:
        return _cmd_frame(CMD_START_ACQ, mode, seq).encode()

    @staticmethod
    def stop_acq(mode: int = 0, seq: int = 0) -> bytes:
        return _cmd_frame(CMD_STOP_ACQ, mode, seq).encode()

    @staticmethod
    def once_acq(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_ONCE_ACQ, 0, seq).encode()

    # 读状态
    @staticmethod
    def read_status(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_READ_STATUS, 0, seq).encode()

    @staticmethod
    def read_info(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_READ_INFO, 0, seq).encode()

    @staticmethod
    def read_bat(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_READ_BAT, 0, seq).encode()

    @staticmethod
    def read_lead(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_READ_LEAD, 0, seq).encode()

    # 复位
    @staticmethod
    def reset_mcu(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_RESET_MCU, 0, seq).encode()

    @staticmethod
    def reset_sensor(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_RESET_SENSOR, 0, seq).encode()

    # OTA
    @staticmethod
    def enter_ota(channel: int = 0, seq: int = 0) -> bytes:
        return _cmd_frame(CMD_ENTER_OTA, channel, seq).encode()

    @staticmethod
    def exit_ota(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_EXIT_OTA, 0, seq).encode()

    # 显示
    @staticmethod
    def set_lcd(bright: int, timeout_s: int = 0, seq: int = 0) -> bytes:
        return _cmd_frame(CMD_SET_LCD, bright & 0xFF, seq).encode()

    @staticmethod
    def set_timeout(timeout_s: int, seq: int = 0) -> bytes:
        return _cmd_frame(CMD_SET_TIMEOUT, timeout_s & 0xFF, seq).encode()

    # 探测 / 紧急停止
    @staticmethod
    def probe(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_PROBE, 0, seq).encode()

    @staticmethod
    def emergency_stop(seq: int = 0) -> bytes:
        return _cmd_frame(CMD_EMERGENCY_STOP, 0, seq).encode()

    # 心跳
    @staticmethod
    def heartbeat(seq: int = 0) -> bytes:
        return Frame(type=TYPE_HEARTBEAT, seq=seq, payload=b"").encode()

    # ACK
    @staticmethod
    def build_ack(acked_type: int, acked_seq: int, status: int = 0, seq: int = 0) -> bytes:
        return Frame(type=TYPE_ACK, seq=seq, payload=struct.pack("<BIB", acked_type, acked_seq, status)).encode()

    # 参数配置
    @staticmethod
    def set_ecg_fs(freq_hz: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_ECG_FS, freq_hz, seq).encode()

    @staticmethod
    def set_pvdf_fs(freq_hz: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_PVDF_FS, freq_hz, seq).encode()

    @staticmethod
    def set_res_fs(freq_hz: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_RES_FS, freq_hz, seq).encode()

    @staticmethod
    def set_ecg_pga(gain: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_ECG_PGA, gain, seq).encode()

    @staticmethod
    def set_pvdf_pga(gain: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_PVDF_PGA, gain, seq).encode()

    @staticmethod
    def set_res_pga(gain: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_RES_PGA, gain, seq).encode()

    @staticmethod
    def set_hr_period(period_s: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_HR_PERIOD, period_s, seq).encode()

    @staticmethod
    def set_lcd_bright(bright: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_LCD_BRIGHT, bright, seq).encode()

    @staticmethod
    def set_lcd_timeout(timeout_s: int, seq: int = 0) -> bytes:
        return _cfg_frame(CFG_LCD_TIMEOUT, timeout_s, seq).encode()
