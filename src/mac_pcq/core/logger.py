"""统一日志。

- 文件 + 控制台双输出
- DEBUG / INFO / WARN / ERROR 四级
- 通过 Qt Signal 把日志事件转发到 UI（解耦 UI 与 logger）
- 使用堆叠装饰器，单实例获取：get_logger("xxx")
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from logging.handlers import RotatingFileHandler
from typing import Optional

# 全局默认格式
_FMT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s"
_DATEFMT = "%H:%M:%S"


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


_initialized = False


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[str] = None,
    console: bool = True,
) -> None:
    """初始化全局日志。仅需调用一次。"""
    global _initialized
    if _initialized:
        return
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    if console:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    if log_dir is None:
        log_dir = os.path.join(os.path.expanduser("~"), ".mac_pcq", "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    root.addHandler(fh)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger。如果尚未初始化，使用默认设置。"""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)


def log_to_ui_signal(logger: logging.Logger, signal_emitter) -> None:
    """把 logger 的输出同时发到 Qt Signal（给 UI 的日志页用）。

    signal_emitter 必须有 emit(level: str, msg: str) 接口。
    """
    class _SignalHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                signal_emitter.emit(record.levelname, self.format(record))
            except Exception:  # noqa: BLE001
                pass

    h = _SignalHandler()
    h.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))
    logger.addHandler(h)
