"""帧编解码 + CRC16-CCITT。

详见 spec.py 的帧格式注释。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

from .spec import MAGIC, PROTO_VER, HEADER_SIZE, CRC_SIZE
from .errors import BadMagicError, CRCMismatchError, TruncatedFrameError

# struct format：
#   <  : little-endian
#   H  : u16 magic
#   B  : u8 ver
#   B  : u8 type
#   I  : u32 seq
#   Q  : u64 ts_us
#   H  : u16 len (payload bytes)
_HEADER_FMT = "<HBB I Q H"
_HEADER_STRUCT = struct.Struct(_HEADER_FMT)  # 2+1+1+4+8+2 = 18


@dataclass
class Frame:
    """协议层统一的帧抽象。

    payload 是原始 bytes，业务含义由 type + parsers 决定。
    """

    ver: int = PROTO_VER
    type: int = 0
    seq: int = 0
    ts_us: int = 0
    payload: bytes = b""

    @property
    def len(self) -> int:
        return len(self.payload)

    @property
    def total_size(self) -> int:
        return HEADER_SIZE + len(self.payload) + CRC_SIZE

    def encode(self) -> bytes:
        """打包为完整字节流（含 CRC）。"""
        if len(self.payload) > 0xFFFF:
            raise ValueError(f"payload too large: {len(self.payload)}")
        body = _HEADER_STRUCT.pack(
            MAGIC, self.ver, self.type,
            self.seq & 0xFFFFFFFF, self.ts_us & 0xFFFFFFFFFFFFFFFF,
            len(self.payload) & 0xFFFF,
        )
        # CRC 计算覆盖 ver+type+seq+ts_us+len+payload（不含 magic）
        crc_region = body[2:] + self.payload
        crc = FrameCodec.crc16_ccitt(crc_region)
        return body + self.payload + struct.pack("<H", crc)

    @classmethod
    def decode(cls, buf: bytes) -> "Frame":
        """对**已对齐**的完整帧做解析。不足 18B 抛 TruncatedFrameError。

        注意：本方法不做 magic 查找；调用方需要先用 find_magic 对齐。
        """
        if len(buf) < HEADER_SIZE:
            raise TruncatedFrameError(need=HEADER_SIZE, got=len(buf))
        magic, ver, ftype, seq, ts_us, plen = _HEADER_STRUCT.unpack_from(buf, 0)
        if magic != MAGIC:
            raise BadMagicError(got=magic)
        total = HEADER_SIZE + plen + CRC_SIZE
        if len(buf) < total:
            raise TruncatedFrameError(need=total, got=len(buf))
        payload = bytes(buf[HEADER_SIZE:HEADER_SIZE + plen])
        crc_region = bytes(buf[2:HEADER_SIZE]) + payload
        expected_crc = struct.unpack_from("<H", buf, HEADER_SIZE + plen)[0]
        actual_crc = FrameCodec.crc16_ccitt(crc_region)
        if expected_crc != actual_crc:
            raise CRCMismatchError(expected=expected_crc, got=actual_crc)
        return cls(ver=ver, type=ftype, seq=seq, ts_us=ts_us, payload=payload)

    @classmethod
    def decode_header(cls, buf: bytes) -> tuple[int, int]:
        """仅解析头部，返回 (frame_total_size, type)。

        用于路由预读，避免解析完整 payload 再分发。
        """
        if len(buf) < HEADER_SIZE:
            raise TruncatedFrameError(need=HEADER_SIZE, got=len(buf))
        magic, _ver, ftype, _seq, _ts_us, plen = _HEADER_STRUCT.unpack_from(buf, 0)
        if magic != MAGIC:
            raise BadMagicError(got=magic)
        return HEADER_SIZE + plen + CRC_SIZE, ftype

    def __repr__(self) -> str:
        return (
            f"Frame(type=0x{self.type:02X}, seq={self.seq}, "
            f"ts_us={self.ts_us}, len={self.len})"
        )


class FrameCodec:
    """无状态工具集：CRC + magic 搜索 + 累加解析。"""

    @staticmethod
    def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
        """CRC16-CCITT（多项式 0x1021，初值 0xFFFF，无反演输入/输出）。

        与 MCU 端 C 实现保持一致：
            uint16_t crc = 0xFFFF;
            for (each byte b):
              crc ^= (b << 8);
              for (i = 0; i < 8; i++):
                crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) : (crc << 1);
                crc &= 0xFFFF;
        """
        crc = init & 0xFFFF
        for b in data:
            crc ^= (b & 0xFF) << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    @staticmethod
    def find_magic(buf: bytes, start: int = 0) -> int:
        """在 buf 中查找 0x55 0xAA（小端）首次出现位置；返回 -1 表示未找到。"""
        # little-endian: 0xAA55 存储为 55 AA
        target = bytes([0x55, 0xAA])
        idx = buf.find(target, start)
        return idx

    @staticmethod
    def feed(buf: bytearray, incoming: bytes, on_frame, on_error=None) -> int:
        """累加式解析：从 incoming 追加到 buf 并尝试切出完整帧。

        - on_frame(frame: Frame)
        - on_error(exc: ProtocolError, raw: bytes)

        返回本次解析掉的字节数（用于滑动窗口）。
        """
        consumed = 0
        if incoming:
            buf.extend(incoming)
        while True:
            idx = FrameCodec.find_magic(bytes(buf))
            if idx < 0:
                # 没找到 magic，全部丢弃
                consumed += len(buf)
                buf.clear()
                return 0
            if idx > 0:
                # 跳过 magic 前的杂数据
                del buf[:idx]
                consumed += idx
            if len(buf) < HEADER_SIZE:
                return consumed
            # decode_header 已经验证了 magic 字段
            try:
                total_size, _ftype = Frame.decode_header(bytes(buf))
            except BadMagicError:
                # find_magic 命中但 magic 字段错误（极少发生），跳过这个字节
                del buf[:1]
                consumed += 1
                continue
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    on_error(exc, bytes(buf[:HEADER_SIZE]))
                del buf[:1]
                consumed += 1
                continue
            if len(buf) < total_size:
                # 帧不完整，等更多字节
                return consumed
            frame_bytes = bytes(buf[:total_size])
            try:
                frame = Frame.decode(frame_bytes)
                on_frame(frame)
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    on_error(exc, frame_bytes)
            del buf[:total_size]
            consumed += total_size
