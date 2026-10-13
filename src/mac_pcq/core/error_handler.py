"""统一错误处理：UserFacingError + 全局异常钩子。

设计原则（参见《UI 设计》§10.2）：
错误必须包含：发生了什么 / 为什么 / 怎么办
禁止把内部异常（CRCError 等）直接暴露给用户。
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from typing import Callable, Optional

from .logger import get_logger

_log = get_logger("error")


@dataclass
class UserFacingError(Exception):
    """面向用户的错误，包含三段信息。"""

    what: str           # 发生了什么
    why: str = ""       # 为什么（可选）
    how: str = ""       # 怎么办（动作）
    detail: str = ""    # 技术细节（折叠展示）
    code: str = ""      # 错误码（用于本地化映射）

    def __str__(self) -> str:
        msg = f"[{self.code}] {self.what}" if self.code else self.what
        if self.why:
            msg += f"\n原因：{self.why}"
        if self.how:
            msg += f"\n处置：{self.how}"
        return msg


# 错误回调：UI 注册后，未处理异常会冒泡到这里
_handler: Optional[Callable[[UserFacingError], None]] = None


def set_error_handler(callback: Callable[[UserFacingError], None]) -> None:
    """UI 启动时注册错误回调。"""
    global _handler
    _handler = callback


def report_error(err: UserFacingError) -> None:
    """统一上报入口。"""
    _log.error("UserFacingError[%s]: %s | why=%s | how=%s",
               err.code, err.what, err.why, err.how)
    if _handler is not None:
        try:
            _handler(err)
        except Exception:  # noqa: BLE001
            _log.exception("error handler raised")


def global_exception_hook(exc_type, exc_value, exc_tb) -> None:
    """sys.excepthook 替换：把未处理异常包成 UserFacingError。"""
    if issubclass(exc_type, UserFacingError):
        report_error(exc_value)
        return
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _log.error("Uncaught exception:\n%s", tb)
    report_error(UserFacingError(
        what="应用发生未处理异常",
        why=str(exc_value) or exc_type.__name__,
        how="请重试；如反复出现，请查看日志并联系维护",
        detail=tb,
    ))


def install_global_hook() -> None:
    """安装全局异常钩子。"""
    sys.excepthook = global_exception_hook
