# intent.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IntentType = Literal[
    "update_prefs",     # 更新/补充偏好
    "generate",         # 生成计划
    "show_prefs",       # 展示当前偏好
    "reset",            # 重置会话
    "help",             # 帮助
]

@dataclass
class Intent:
    type: IntentType

def detect_intent(text: str) -> Intent:
    t = text.strip().lower()

    # 帮助
    if any(k in t for k in ["帮助", "怎么用", "help", "示例"]):
        return Intent("help")

    # 重置
    if any(k in t for k in ["重置", "清空", "reset", "重新开始"]):
        return Intent("reset")

    # 展示偏好
    if any(k in t for k in ["当前", "偏好", "参数", "你记住了什么", "show"]):
        return Intent("show_prefs")

    # 生成/输出
    if any(k in t for k in ["生成", "开始", "输出", "做吧", "go", "run"]):
        return Intent("generate")

    # 默认：当作更新偏好
    return Intent("update_prefs")