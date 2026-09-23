"""SessionService：采集会话状态机。

状态转换（不可跳级）：
    IDLE → STARTING → RUNNING ⇄ PAUSED
                         ↓
                       RECORDING (RUNNING + record=True)
                         ↓
                       STOPPING → IDLE
    任意状态 → ERROR → IDLE
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Callable, Optional


class SessionState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    RECORDING = "recording"
    STOPPING = "stopping"
    ERROR = "error"


# 合法转换表
_VALID: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.STARTING, SessionState.ERROR},
    SessionState.STARTING: {SessionState.RUNNING, SessionState.ERROR, SessionState.IDLE},
    SessionState.RUNNING: {SessionState.PAUSED, SessionState.STOPPING, SessionState.RECORDING, SessionState.ERROR},
    SessionState.PAUSED: {SessionState.RUNNING, SessionState.STOPPING, SessionState.ERROR},
    SessionState.RECORDING: {SessionState.RUNNING, SessionState.STOPPING, SessionState.ERROR},
    SessionState.STOPPING: {SessionState.IDLE, SessionState.ERROR},
    SessionState.ERROR: {SessionState.IDLE},
}


class SessionService:
    """管理一次采集会话的生命周期。

    通过 on_state_changed 通知上层；通过 send_cmd 发送下行命令（依赖外部注入）。
    """

    def __init__(
        self,
        send_cmd: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        self._state: SessionState = SessionState.IDLE
        self._send_cmd = send_cmd or (lambda b: None)
        self._state_cbs: list[Callable[[SessionState], None]] = []
        self._recording: bool = False
        self._mode: int = 0

    # ---- 状态查询 ----
    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._recording

    # ---- 状态订阅 ----
    def on_state_changed(self, cb: Callable[[SessionState], None]) -> None:
        self._state_cbs.append(cb)

    def _set_state(self, s: SessionState) -> None:
        if s == self._state:
            return
        if s not in _VALID[self._state]:
            raise RuntimeError(f"illegal transition {self._state.value} -> {s.value}")
        self._state = s
        for cb in self._state_cbs:
            try:
                cb(s)
            except Exception:  # noqa: BLE001
                pass

    # ---- 业务动作 ----
    async def start(self, mode: int = 0, record: bool = False) -> None:
        """开始采集。若已在 RUNNING/RECORDING 则先 stop 再启动。"""
        if self._state in (SessionState.RUNNING, SessionState.RECORDING, SessionState.PAUSED):
            await self.stop()
        self._set_state(SessionState.STARTING)
        self._mode = mode
        from ..protocol.commands import CommandBuilder
        try:
            self._send_cmd(CommandBuilder.start_acq(mode=mode))
        except Exception:  # noqa: BLE001
            self._set_state(SessionState.ERROR)
            raise
        self._set_state(SessionState.RUNNING)
        if record:
            self._set_state(SessionState.RECORDING)
            self._recording = True

    async def pause(self) -> None:
        if self._state != SessionState.RUNNING:
            return
        # 真实设备可发 pause 命令；本轮 stub
        self._set_state(SessionState.PAUSED)

    async def resume(self) -> None:
        if self._state != SessionState.PAUSED:
            return
        self._set_state(SessionState.RUNNING)

    async def stop(self) -> None:
        if self._state in (SessionState.IDLE, SessionState.STOPPING):
            return
        self._set_state(SessionState.STOPPING)
        from ..protocol.commands import CommandBuilder
        try:
            self._send_cmd(CommandBuilder.stop_acq(mode=self._mode))
        finally:
            self._recording = False
            self._set_state(SessionState.IDLE)

    async def fail(self, reason: str = "") -> None:
        """进入错误态（外部异常时调用）。"""
        self._recording = False
        self._set_state(SessionState.ERROR)

    async def reset(self) -> None:
        """ERROR → IDLE 复位。"""
        if self._state == SessionState.ERROR:
            self._set_state(SessionState.IDLE)
