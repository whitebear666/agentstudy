# intent.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IntentType = Literal[
    "update_prefs",
    "generate",
    "show_prefs",
    "reset",
    "help",
    "undo",
]

@dataclass
class Intent:
    type: IntentType

def detect_intent(text: str) -> Intent:
    t = text.strip().lower()

    if any(k in t for k in ["帮助", "怎么用", "help", "示例"]):
        return Intent("help")

    if any(k in t for k in ["撤销", "undo", "回退", "上一步"]):
        return Intent("undo")

    if any(k in t for k in ["重置", "清空", "reset", "重新开始"]):
        return Intent("reset")

    if any(k in t for k in ["当前", "偏好", "参数", "你记住了什么", "show"]):
        return Intent("show_prefs")

    if any(k in t for k in ["生成", "开始", "输出", "做吧", "go", "run", "完成", "好了", "就这样", "ok"]):
        return Intent("generate")

    return Intent("update_prefs")