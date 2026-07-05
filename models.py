"""核心数据模型。

作用：
    定义整个项目中共享的数据结构，包括用户偏好、菜谱、一餐组合、
    一天菜单，以及菜谱的难度/时间/评分元信息。

关联模块：
    agent.py 读取和生成这些模型。
    conversation.py 在多轮对话中保存 UserPrefs。
    skills/cooking_profile.py 负责填充 RecipeMeta。
    skills/meal_composer.py 负责组合 MealSet。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RecipeMeta:
    difficulty: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    score: Optional[float] = None
    time_source: str = "estimated"


@dataclass
class UserPrefs:
    people: int = 2
    days: int = 3
    budget: Optional[float] = None
    avoid: Optional[List[str]] = None
    cuisine: str = "家常"
    has_kitchen: bool = True
    dish_count: Optional[int] = None
    meat_count: Optional[int] = None
    vegetable_count: Optional[int] = None
    breakfast_style: Optional[str] = None
    lunch_style: Optional[str] = None
    dinner_style: Optional[str] = None
    health_goal: Optional[str] = None
    favorite_recipes: Optional[List[str]] = None


@dataclass
class Meal:
    name: str
    ingredients: Dict[str, str]
    steps: List[str]
    meta: RecipeMeta = field(default_factory=RecipeMeta)


@dataclass
class MealSet:
    main: Meal
    side: Optional[Meal] = None
    staple: Optional[Meal] = None
    soup: Optional[Meal] = None


@dataclass
class DayPlan:
    day_index: int
    breakfast: MealSet
    lunch: MealSet
    dinner: MealSet
