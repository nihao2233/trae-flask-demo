"""Design Token（参见《UI 设计》§3）。

集中放置颜色 / 字号 / 间距 / 圆角 / 阴影常量，
所有 UI 文件不得硬编码这些值。

颜色采用两套：浅色（默认）+ 深色，通过 toggle_theme() 切换。
"""

from __future__ import annotations

# ---- 通道色（不随主题变）----
CHANNEL_COLORS = {
    0: "#6355FF",   # ch-1 紫
    1: "#00B14F",   # ch-2 绿
    2: "#FF7A45",   # ch-3 橙
    3: "#1B6FF9",   # ch-4 蓝
}

# ---- 浅色主题（默认）----
LIGHT = {
    "brand_primary": "#6355FF",
    "brand_primary_hover": "#4F45E0",
    "brand_primary_disabled": "#B8B3FF",
    "accent_success": "#00B14F",
    "accent_warning": "#FF7A45",
    "accent_danger": "#E5453D",
    "accent_info": "#1B6FF9",
    "text_primary": "#1F1F1F",
    "text_secondary": "#5C5C5C",
    "text_tertiary": "#9A9A9A",
    "text_inverse": "#FFFFFF",
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F5F5F5",
    "bg_tertiary": "#FAFAFA",
    "border_default": "#E0E0E0",
    "border_strong": "#C0C0C0",
    "shadow_1": "0 1px 2px rgba(0,0,0,0.06)",
    "shadow_2": "0 4px 12px rgba(0,0,0,0.10)",
}

# ---- 深色主题 ----
DARK = {
    "brand_primary": "#7A6FFF",
    "brand_primary_hover": "#9B8FFF",
    "brand_primary_disabled": "#5C5380",
    "accent_success": "#00C75A",
    "accent_warning": "#FF9966",
    "accent_danger": "#FF6657",
    "accent_info": "#5C9CFF",
    "text_primary": "#F0F0F0",
    "text_secondary": "#B8B8B8",
    "text_tertiary": "#808080",
    "text_inverse": "#1A1A1A",
    "bg_primary": "#1A1A1A",
    "bg_secondary": "#2A2A2A",
    "bg_tertiary": "#222222",
    "border_default": "#3A3A3A",
    "border_strong": "#5C5C5C",
    "shadow_1": "0 1px 2px rgba(0,0,0,0.30)",
    "shadow_2": "0 4px 12px rgba(0,0,0,0.50)",
}

# ---- 字号 ----
FONT = {
    "display": (28, 700, 1.2),    # 心率 / 呼吸率大数字
    "h1": (22, 700, 1.3),
    "h2": (18, 600, 1.3),
    "h3": (16, 600, 1.4),
    "body": (14, 400, 1.5),
    "small": (12, 400, 1.4),
    "tiny": (11, 400, 1.3),
}

# ---- 间距 ----
SPACE = {
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 24,
    6: 32,
}

# ---- 圆角 ----
RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
    "full": 9999,
}

# ---- 动画时长（ms）----
DURATION = {
    "fast": 120,
    "normal": 200,
    "slow": 400,
}

# ---- 色阶基色（6 种，UI 设计 §6.2.3）----
COLOR_BASES = {
    "blue_red": ["#1B6FF9", "#6355FF", "#FF7A45", "#E5453D"],
    "blue_green": ["#1B6FF9", "#00B14F"],
    "purple_yellow": ["#6355FF", "#FFD93D"],
    "gray": ["#F0F0F0", "#1F1F1F"],
    "rainbow": ["#9B59B6", "#3498DB", "#1ABC9C", "#F1C40F", "#E74C3C"],
    "thermal": ["#000000", "#9B00FF", "#FF0000", "#FFFF00", "#FFFFFF"],
}


# ---- 当前主题 + 切换 ----
_current_theme_name: str = "light"
_subscribers: list = []


def current() -> dict:
    return LIGHT if _current_theme_name == "light" else DARK


def name() -> str:
    return _current_theme_name


def set_theme(name: str) -> None:
    """切换主题并通知所有订阅者。"""
    global _current_theme_name
    if name not in ("light", "dark"):
        return
    if name == _current_theme_name:
        return
    _current_theme_name = name
    for cb in _subscribers:
        try:
            cb(name)
        except Exception:  # noqa: BLE001
            pass


def toggle() -> str:
    """在浅 / 深之间切换，返回新主题名。"""
    new = "dark" if _current_theme_name == "light" else "light"
    set_theme(new)
    return new


def subscribe(callback) -> None:
    """订阅主题变化（callback(name: str)）。"""
    _subscribers.append(callback)


def get_theme(name: str = "light") -> dict:
    return LIGHT if name == "light" else DARK
