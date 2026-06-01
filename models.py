from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class UserPrefs:
    people: int = 2
    days: int = 3
    budget: Optional[float] = None
    avoid: Optional[List[str]] = None
    cuisine: str = "家常"
    has_kitchen: bool = True


@dataclass
class Meal:
    name: str
    ingredients: Dict[str, str]
    steps: List[str]


@dataclass
class MealSet:
    """
    一餐的结构化组合：
    - main：主菜（可荤可素，但优先荤/蛋白）
    - side：配菜（通常素菜）
    - staple：主食（米饭/面/粥/饼等）
    - soup：汤（可选）
    """
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