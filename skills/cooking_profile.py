"""菜谱烹饪画像模块。

作用：
    从菜谱文本中抽取或估算烹饪难度、预计时间、推荐评分，并为一餐
    生成粗粒度时间规划。

关联模块：
    models.py 提供 Meal、MealSet、RecipeMeta。
    agent.py 在加载菜谱和渲染菜单时调用本模块。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from models import Meal, MealSet, RecipeMeta


CN_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "半": 0.5,
}

METHOD_TIME_DEFAULTS = {
    "炒": 20,
    "煎": 20,
    "炸": 35,
    "炖": 70,
    "煮": 35,
    "蒸": 30,
    "烤": 45,
    "拌": 15,
    "凉拌": 15,
    "微波": 10,
    "空气炸": 25,
}

METHOD_DIFFICULTY_DEFAULTS = {
    "炒": 2,
    "煎": 2,
    "炸": 4,
    "炖": 3,
    "煮": 2,
    "蒸": 2,
    "烤": 3,
    "拌": 1,
    "凉拌": 1,
    "微波": 1,
    "空气炸": 2,
}


@dataclass
class CookingTimelineItem:
    offset_minutes: int
    title: str


def _cn_number_to_float(text: str) -> Optional[float]:
    text = text.strip()
    if not text:
        return None
    if text in CN_NUMBERS:
        return float(CN_NUMBERS[text])
    if text == "十":
        return 10.0
    if text.startswith("十") and len(text) == 2:
        right = CN_NUMBERS.get(text[1])
        return 10.0 + float(right or 0)
    if text.endswith("十") and len(text) == 2:
        left = CN_NUMBERS.get(text[0])
        return float(left or 1) * 10.0
    if "十" in text:
        left, right = text.split("十", 1)
        left_num = CN_NUMBERS.get(left, 1) if left else 1
        right_num = CN_NUMBERS.get(right, 0) if right else 0
        return float(left_num * 10 + right_num)
    return None


def _number_to_minutes(value: str, unit: str) -> Optional[int]:
    value = value.strip()
    try:
        number = float(value)
    except ValueError:
        number = _cn_number_to_float(value)
    if number is None:
        return None
    if "小时" in unit or "鐘頭" in unit:
        return int(round(number * 60))
    return int(round(number))


def extract_difficulty(text: str) -> Optional[int]:
    match = re.search(r"难度[：:\s]*([★☆]{1,5})", text)
    if match:
        return max(1, min(5, match.group(1).count("★")))

    match = re.search(r"([一二两三四五12345])\s*星", text)
    if match:
        raw = match.group(1)
        value = int(raw) if raw.isdigit() else int(CN_NUMBERS.get(raw, 0))
        return max(1, min(5, value)) if value else None

    if any(word in text for word in ["非常简单", "极其简单", "零门槛"]):
        return 1
    if any(word in text for word in ["简单", "新手友好", "容易上手"]):
        return 2
    if any(word in text for word in ["适中", "中等难度"]):
        return 3
    if any(word in text for word in ["有一定挑战", "稍高", "不太友好"]):
        return 4
    if any(word in text for word in ["较高", "很难", "复杂"]):
        return 5
    return None


def extract_cook_time_minutes(text: str) -> Optional[int]:
    values: List[int] = []

    range_match = re.search(
        r"(\d+(?:\.\d+)?|[一二两三四五六七八九十半]+)\s*[-到至~]\s*(\d+(?:\.\d+)?|[一二两三四五六七八九十半]+)\s*(分钟|小时)",
        text,
    )
    if range_match:
        left = _number_to_minutes(range_match.group(1), range_match.group(3))
        right = _number_to_minutes(range_match.group(2), range_match.group(3))
        if left and right:
            values.append(int(round((left + right) / 2)))

    matches = re.findall(r"(\d+(?:\.\d+)?|[一二两三四五六七八九十半]+)\s*(分钟|小时)", text)
    values.extend(
        minutes
        for raw, unit in matches
        for minutes in [_number_to_minutes(raw, unit)]
        if minutes is not None
    )
    if not values:
        return None

    # Recipe text often mixes total time with short step timers; the largest value is
    # usually the best approximation of total elapsed cooking time.
    return max(values)


def estimate_from_methods(methods: Iterable[str]) -> tuple[int, int]:
    method_list = list(methods)
    times = [METHOD_TIME_DEFAULTS[m] for m in method_list if m in METHOD_TIME_DEFAULTS]
    difficulties = [METHOD_DIFFICULTY_DEFAULTS[m] for m in method_list if m in METHOD_DIFFICULTY_DEFAULTS]
    return max(times or [25]), max(difficulties or [2])


def build_recipe_meta(name: str, steps: List[str], tags: dict | None = None) -> RecipeMeta:
    text = "\n".join([name] + steps)
    tags = tags or {}
    methods = tags.get("method", []) if isinstance(tags.get("method", []), list) else []
    fallback_time, fallback_difficulty = estimate_from_methods([str(m) for m in methods])

    difficulty = extract_difficulty(text) or fallback_difficulty
    cook_time = extract_cook_time_minutes(text) or fallback_time

    score = 4.0
    if cook_time <= 20:
        score += 0.25
    elif cook_time >= 90:
        score -= 0.2
    if difficulty <= 2:
        score += 0.25
    elif difficulty >= 4:
        score -= 0.15
    if methods:
        score += 0.1
    score = max(1.0, min(5.0, round(score, 1)))

    return RecipeMeta(
        difficulty=max(1, min(5, difficulty)),
        cook_time_minutes=max(1, cook_time),
        score=score,
        time_source="parsed" if extract_cook_time_minutes(text) else "estimated",
    )


def iter_mealset_meals(mealset: MealSet) -> List[Meal]:
    return [meal for meal in [mealset.main, mealset.side, mealset.staple, mealset.soup] if meal]


def _method_text(meal: Meal) -> str:
    return meal.name + "\n" + "\n".join(meal.steps)


def _is_waiting_friendly(meal: Meal) -> bool:
    text = _method_text(meal)
    return any(keyword in text for keyword in ["炖", "煮", "蒸", "烤", "焖", "卤", "腌", "煲"])


def _active_minutes(meal: Meal) -> int:
    total = meal.meta.cook_time_minutes or 25
    difficulty = meal.meta.difficulty or 2
    if _is_waiting_friendly(meal):
        ratio = 0.38 + difficulty * 0.04
    else:
        ratio = 0.68 + difficulty * 0.03
    return max(6, min(total, int(round(total * ratio))))


def mealset_total_time(mealset: MealSet) -> int:
    meals = iter_mealset_meals(mealset)
    if not meals:
        return 0
    times = [meal.meta.cook_time_minutes or 25 for meal in meals]
    if len(times) == 1:
        return times[0]
    longest = max(meals, key=lambda meal: meal.meta.cook_time_minutes or 25)
    remaining_active = sum(_active_minutes(meal) for meal in meals if meal is not longest)
    overlap_ratio = 0.55 if _is_waiting_friendly(longest) else 0.35
    extra = int(round(remaining_active * (1 - overlap_ratio)))
    return max(times) + min(25, max(5, extra))


def build_mealset_timeline(mealset: MealSet) -> List[CookingTimelineItem]:
    meals = sorted(
        iter_mealset_meals(mealset),
        key=lambda meal: meal.meta.cook_time_minutes or 25,
        reverse=True,
    )
    if not meals:
        return []

    total = mealset_total_time(mealset)
    longest = meals[0]
    items = [CookingTimelineItem(0, f"先启动耗时最长的菜：{longest.name}")]

    if len(meals) >= 2:
        if _is_waiting_friendly(longest):
            items.append(CookingTimelineItem(5, f"利用等待时间洗切备菜：{meals[1].name}"))
        else:
            items.append(CookingTimelineItem(max(5, _active_minutes(longest) // 2), f"主菜进入稳定阶段后准备：{meals[1].name}"))

    if len(meals) >= 3:
        third_start = max(10, min(total - 15, total // 2))
        items.append(CookingTimelineItem(third_start, f"并行处理快手菜/汤/主食：{meals[2].name}"))

    if len(meals) >= 4:
        fourth_start = max(15, min(total - 10, total * 2 // 3))
        items.append(CookingTimelineItem(fourth_start, f"最后补齐低风险步骤：{meals[3].name}"))

    items.append(CookingTimelineItem(max(0, total - 5), "统一调味、装盘、确认主食和汤品温度"))
    return sorted(items, key=lambda item: item.offset_minutes)


def stars(value: Optional[int]) -> str:
    value = max(1, min(5, value or 1))
    return "★" * value + "☆" * (5 - value)
