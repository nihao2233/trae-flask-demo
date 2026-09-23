"""跨平台用户目录工具。"""

from __future__ import annotations

import os
import tempfile

APP_DIRNAME = "mac_pcq"


def _base() -> str:
    if os.name == "nt":
        return os.environ.get("APPDATA") or os.path.join(tempfile.gettempdir(), APP_DIRNAME)
    return os.path.join(os.path.expanduser("~"), ".config", APP_DIRNAME)


def user_data_dir() -> str:
    d = os.path.join(_base(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def user_log_dir() -> str:
    d = os.path.join(_base(), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def user_config_path() -> str:
    d = _base()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "config.json")
