"""协议层错误。

协议层本身的异常（CRC / magic / 截断）属于内部错误，
由 dispatcher 上报到 logger，必要时再 wrap 成 UserFacingError。
"""

from __future__ import annotations


class ProtocolError(Exception):
    """协议层内部错误基类。"""

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)


class CRCMismatchError(ProtocolError):
    """CRC 校验失败。"""

    def __init__(self, expected: int, got: int) -> None:
        super().__init__(f"CRC mismatch: expected=0x{expected:04X} got=0x{got:04X}")
        self.expected = expected
        self.got = got


class BadMagicError(ProtocolError):
    """magic 字段错误。"""

    def __init__(self, got: int) -> None:
        super().__init__(f"bad magic: got=0x{got:04X}")


class TruncatedFrameError(ProtocolError):
    """帧不完整。"""

    def __init__(self, need: int, got: int) -> None:
        super().__init__(f"truncated: need={need} got={got}")


class UnknownTypeError(ProtocolError):
    """未知 type。"""

    def __init__(self, ftype: int) -> None:
        super().__init__(f"unknown type: 0x{ftype:02X}")
