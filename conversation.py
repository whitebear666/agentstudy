from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set

from models import UserPrefs


@dataclass
class ConversationState:
    # 最新偏好（可逐步补全/覆盖）
    prefs: UserPrefs = field(default_factory=lambda: UserPrefs(
        people=2,
        days=3,
        budget=None,
        avoid=None,
        cuisine="家常",
        has_kitchen=True,
        breakfast_style=None,
        lunch_style=None,
        dinner_style=None,
    ))

    # 对话历史（目前主要用于未来扩展；追问逻辑不再依赖 history 猜测）
    history: List[Dict[str, str]] = field(default_factory=list)

    # 标记哪些字段是“用户明确确认/设置过”的（区别于默认值）
    confirmed_fields: Set[str] = field(default_factory=set)

    def update_from_partial(self, partial: Dict[str, Any]) -> None:
        """
        partial: {"people":..., "days":..., "budget":..., "avoid":..., "cuisine":..., ...}
        约定：
          - None 表示“本轮没提/不更新”（除 budget 外：budget 允许 None 表示‘不限’，由 extractor/command 决定是否带键）
          - avoid: [] 表示“无忌口/清空忌口”
        """
        if "people" in partial and partial["people"] is not None:
            self.prefs.people = int(partial["people"])
            self.confirmed_fields.add("people")

        if "days" in partial and partial["days"] is not None:
            self.prefs.days = int(partial["days"])
            self.confirmed_fields.add("days")

        if "budget" in partial:
            # 只要 partial 里出现 budget 键，就视为用户对预算表达了意见（即使是 None=不限）
            self.prefs.budget = partial["budget"]
            self.confirmed_fields.add("budget")

        if "avoid" in partial and partial["avoid"] is not None:
            # 允许 [] 表示“无忌口/清空忌口”
            self.prefs.avoid = partial["avoid"]
            self.confirmed_fields.add("avoid")

        if "cuisine" in partial and partial["cuisine"]:
            self.prefs.cuisine = str(partial["cuisine"]).strip()
            self.confirmed_fields.add("cuisine")

        # 餐次级偏好（仅用户明确说到才更新）
        if "breakfast_style" in partial and partial["breakfast_style"]:
            self.prefs.breakfast_style = str(partial["breakfast_style"]).strip()
            self.confirmed_fields.add("breakfast_style")

        if "lunch_style" in partial and partial["lunch_style"]:
            self.prefs.lunch_style = str(partial["lunch_style"]).strip()
            self.confirmed_fields.add("lunch_style")

        if "dinner_style" in partial and partial["dinner_style"]:
            self.prefs.dinner_style = str(partial["dinner_style"]).strip()
            self.confirmed_fields.add("dinner_style")

        if "health_goal" in partial:
            self.prefs.health_goal = partial["health_goal"]
            self.confirmed_fields.add("health_goal")