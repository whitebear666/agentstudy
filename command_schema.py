from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal


CommandIntent = Literal[
    "update_prefs",
    "generate",
    "show_prefs",
    "reset",
    "undo",
    "help",
]


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
        if not isinstance(updates, dict):
            updates = {}
        # 仅保留允许的 keys（防止模型乱输出）
        allowed = {"people", "days", "budget", "avoid", "cuisine", "dinner_style"}
        updates = {k: v for k, v in updates.items() if k in allowed}
        return Command(intent=intent, updates=updates)