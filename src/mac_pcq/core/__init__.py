"""跨切关注点：日志 / 配置 / 错误 / 度量 / 常量 / 国际化。"""
from .constants import APP_NAME, APP_VERSION, DEFAULT_ECG_FS, DEFAULT_WINDOW_S
from .logger import get_logger, setup_logging, LogLevel
from .error_handler import UserFacingError, global_exception_hook

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "DEFAULT_ECG_FS",
    "DEFAULT_WINDOW_S",
    "get_logger",
    "setup_logging",
    "LogLevel",
    "UserFacingError",
    "global_exception_hook",
]
