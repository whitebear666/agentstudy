# conversation.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from models import UserPrefs


@dataclass
class ConversationState:
    # 最新偏好（可逐步补全/覆盖）
    prefs: UserPrefs = field(default_factory=lambda: UserPrefs(
        people=2, days=3, budget=None, avoid=None, cuisine="家常", has_kitchen=True
    ))
    # 记录对话历史（可选：未来做更强的上下文提示）
    history: List[Dict[str, str]] = field(default_factory=list)

    def update_from_partial(self, partial: Dict[str, Any]) -> None:
        """
        partial: {"people":..., "days":..., "budget":..., "avoid":..., "cuisine":...}
        只更新 partial 中非空/非 None 的字段。
        """
        if "people" in partial and partial["people"] is not None:
            self.prefs.people = int(partial["people"])
        if "days" in partial and partial["days"] is not None:
            self.prefs.days = int(partial["days"])
        if "budget" in partial:
            self.prefs.budget = partial["budget"]  # 允许 None 覆盖（表示用户说“不限”）
        if "avoid" in partial and partial["avoid"] is not None:
            self.prefs.avoid = partial["avoid"] or None
        if "cuisine" in partial and partial["cuisine"]:
            self.prefs.cuisine = str(partial["cuisine"])