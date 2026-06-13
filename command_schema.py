from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

CommandIntent = Literal[
    "update_prefs",
    "generate",
    "show_prefs",
    "reset",
    "undo",
    "help",
    "show_menu",  # 新增：显示当前菜单
    "replace",  # 新增：替换某道菜
    "show_pantry",      # 新增：查看冰箱
    "update_pantry",    # 新增：更新冰箱库存
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

    # replace 命令专用字段
    day: Optional[int] = None  # 第几天
    meal_type: Optional[str] = None  # breakfast/lunch/dinner
    part_type: Optional[str] = None  # main/side/staple/soup（可选）
    constraint: Optional[str] = None  # 约束条件，如"清淡的"、"鱼"、"肉类"

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Command":
        intent = d.get("intent", "update_prefs")
        updates = d.get("updates", {})

        if not isinstance(intent, str):
            intent = "update_prefs"
        if intent not in ("update_prefs", "generate", "show_prefs", "reset", "undo", "help", "show_menu", "replace"):
            intent = "update_prefs"

        if not isinstance(updates, dict):
            updates = {}

        # 白名单过滤：避免模型输出奇怪字段导致程序侧混乱
        updates = {k: v for k, v in updates.items() if k in _ALLOWED_UPDATE_KEYS}

        # 提取 replace 命令的专用字段
        day = d.get("day")
        meal_type = d.get("meal_type")
        part_type = d.get("part_type", "main")
        constraint = d.get("constraint")

        # 类型转换和验证
        if day is not None:
            try:
                day = int(day)
            except (ValueError, TypeError):
                day = None

        if meal_type is not None and isinstance(meal_type, str):
            # 支持中文输入
            meal_type_map = {
                "早餐": "breakfast",
                "午餐": "lunch",
                "晚餐": "dinner",
            }
            meal_type = meal_type_map.get(meal_type, meal_type)
            if meal_type not in ("breakfast", "lunch", "dinner"):
                meal_type = None

        if part_type is not None and isinstance(part_type, str):
            part_type_map = {
                "主菜": "main",
                "配菜": "side",
                "主食": "staple",
                "汤": "soup",
            }
            part_type = part_type_map.get(part_type, part_type)
            if part_type not in ("main", "side", "staple", "soup"):
                part_type = "main"

        if constraint is not None and not isinstance(constraint, str):
            constraint = str(constraint) if constraint else None

        return Command(
            intent=intent,
            updates=updates,
            day=day,
            meal_type=meal_type,
            part_type=part_type,
            constraint=constraint,
        )