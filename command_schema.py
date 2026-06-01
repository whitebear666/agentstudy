from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal


CommandIntent = Literal[
    "update_prefs",
    "generate",
    "show_prefs",
    "reset",
    "undo",
    "help",
]


_ALLOWED_UPDATE_KEYS = {
    "people",
    "days",
    "budget",
    "avoid",
    "cuisine",
    "breakfast_style",
    "lunch_style",
    "dinner_style",
}


@dataclass
class Command:
    intent: CommandIntent
    updates: Dict[str, Any]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Command":
        intent = d.get("intent", "update_prefs")
        updates = d.get("updates", {})

        if not isinstance(intent, str):
            intent = "update_prefs"
        if intent not in ("update_prefs", "generate", "show_prefs", "reset", "undo", "help"):
            intent = "update_prefs"

        if not isinstance(updates, dict):
            updates = {}

        # 白名单过滤：避免模型输出奇怪字段导致程序侧混乱
        updates = {k: v for k, v in updates.items() if k in _ALLOWED_UPDATE_KEYS}

        return Command(intent=intent, updates=updates)