"""平台相关封装（路径 / Windows 串口枚举）。"""
from .paths import user_data_dir, user_log_dir, user_config_path
from . import windows  # noqa: F401

__all__ = ["user_data_dir", "user_log_dir", "user_config_path"]
