"""国际化（i18n）占位。

完整 i18n 走 Qt tr() + .ts/.qm 文件；本模块先提供语言切换接口，
供 config 与日志提示使用。
"""

from __future__ import annotations

from typing import Callable

_current_language: str = "zh-CN"
_subscribers: list[Callable[[str], None]] = []


def get_language() -> str:
    return _current_language


def set_language(lang: str) -> None:
    global _current_language
    if lang not in ("zh-CN", "en-US"):
        return
    if lang == _current_language:
        return
    _current_language = lang
    for cb in _subscribers:
        try:
            cb(lang)
        except Exception:  # noqa: BLE001
            pass


def subscribe(callback: Callable[[str], None]) -> None:
    _subscribers.append(callback)
