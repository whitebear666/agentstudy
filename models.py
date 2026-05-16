# models.py
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class UserPrefs:
    people: int = 1
    days: int = 3
    budget: Optional[float] = None
    avoid: List[str] = None  # 忌口/过敏
    cuisine: str = "家常"
    has_kitchen: bool = True

@dataclass
class Meal:
    name: str
    ingredients: Dict[str, str]   # 食材 -> 用量（文本）
    steps: List[str]

@dataclass
class DayPlan:
    day_index: int
    breakfast: Meal
    lunch: Meal
    dinner: Meal