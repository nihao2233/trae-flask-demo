"""用户偏好配置。

不依赖 Qt，使用内置 json + %APPDATA% 路径，
方便后续测试与无头场景使用。
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict

_DEFAULTS: Dict[str, Any] = {
    "theme": "light",                # light / dark
    "language": "zh-CN",             # zh-CN / en-US
    "last_port": "",                 # 上次使用的串口
    "last_baudrate": 115200,
    "ecg_fs": 500,
    "pvdf_fs": 500,
    "resistive_fs": 50,
    "ecg_y_range_mv": 1.0,
    "pvdf_y_range_mv": 10.0,
    "window_seconds": 5.0,
    "matrix_color_base": "blue_red", # 见 ui/theme.py ColorBase
    "matrix_show_format": "resistance",  # resistance / pressure
    "calibration": {
        "a1": 0.01,
        "a2": 0.005,
        "b": 25.0,
        "breakpoint_kohm": 10.0,
    },
    "window_geometry": "",           # base64 encoded QByteArray 字符串
    "recent_files": [],              # 最近打开文件列表
}


def _config_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(
            tempfile.gettempdir(), "mac_pcq"
        )
    else:
        base = os.path.join(os.path.expanduser("~"), ".config", "mac_pcq")
    d = os.path.join(base, "mac_pcq")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "config.json")


class Config:
    """线程安全的用户配置（最简版，使用 json 文件）。"""

    def __init__(self, path: str | None = None) -> None:
        self._path = path or _config_path()
        self._data: Dict[str, Any] = dict(_DEFAULTS)
        self.load()

    def load(self) -> None:
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # 仅合并已知 key，避免破坏后续升级
                for k, v in loaded.items():
                    if k in self._data:
                        if isinstance(self._data[k], dict) and isinstance(v, dict):
                            self._data[k].update(v)
                        else:
                            self._data[k] = v
            except (OSError, json.JSONDecodeError):
                pass

    def save(self) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)
