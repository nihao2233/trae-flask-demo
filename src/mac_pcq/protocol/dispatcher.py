"""Frame 分发：把 Frame 按 type 解析后投递给 DataBus。"""

from __future__ import annotations

from typing import Callable, Optional

from ..core.logger import get_logger
from .codec import Frame, FrameCodec
from .parsers import parse
from .errors import ProtocolError

_log = get_logger("protocol.dispatcher")


class FrameDispatcher:
    """Frame → DataBus 的桥接。

    持有 DataBus 引用 + 解析错误回调。
    """

    def __init__(self, on_payload, on_error: Optional[Callable[[ProtocolError, bytes], None]] = None) -> None:
        """on_payload: Callable[(type:int, seq:int, model), None]"""
        self._on_payload = on_payload
        self._on_error = on_error
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        """喂入字节流（可能包含 0/N 帧）。"""
        FrameCodec.feed(
            self._buf,
            data,
            on_frame=self._handle,
            on_error=self._handle_err,
        )

    def _handle(self, frame: Frame) -> None:
        try:
            model = parse(frame.type, frame.payload, frame.seq)
        except ProtocolError as e:
            self._handle_err(e, frame.payload)
            return
        except Exception as e:  # noqa: BLE001
            _log.warning("parse type=0x%02X failed: %s", frame.type, e)
            return
        try:
            self._on_payload(frame.type, frame.seq, model)
        except Exception:  # noqa: BLE001
            _log.exception("on_payload raised")

    def _handle_err(self, exc: ProtocolError, raw: bytes) -> None:
        _log.warning("protocol error: %s (raw %d bytes)", exc, len(raw))
        if self._on_error:
            try:
                self._on_error(exc, raw)
            except Exception:  # noqa: BLE001
                _log.exception("on_error raised")
