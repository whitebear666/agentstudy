"""一餐组合模块。

作用：
    将候选菜谱组合成结构化的一餐：主菜、配菜、主食、汤。它尽量避免
    重复菜品，并按分类结果选择合适位置。

关联模块：
    models.py 提供 Meal、MealSet、UserPrefs。
    skills/meal_classifier.py 判断菜品类型。
    agent.py 调用本模块生成早餐、午餐、晚餐。
"""

# skills/meal_composer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from models import Meal, MealSet, UserPrefs
from skills.meal_classifier import MealClassifierSkill


@dataclass
class CandidateMeal:
    meal: Meal
    tags: Dict


class MealComposerSkill:
    """
    负责把一堆候选 Meal 组合成结构化的一餐：
    main + side + staple + soup(optional)
    """

    def __init__(self):
        self.classifier = MealClassifierSkill()

    def _pick_one(self, pool: List[CandidateMeal], used_names: Set[str]) -> Optional[CandidateMeal]:
        for c in pool:
            if c.meal.name not in used_names:
                return c
        # 允许重复的兜底
        return pool[0] if pool else None

    def compose_mealset(
        self,
        prefs: UserPrefs,
        candidates: List[CandidateMeal],
        used_names: Set[str],
        want_soup: bool = True,
        want_staple: bool = True,
        want_side: bool = True,
        prefer_protein: bool = True,
    ) -> MealSet:
        # 特征打分：尽量稳定（不随机），利于复现
        mains: List[CandidateMeal] = []
        sides: List[CandidateMeal] = []
        staples: List[CandidateMeal] = []
        soups: List[CandidateMeal] = []

        for c in candidates:
            f = self.classifier.classify(c.meal.name, c.meal.ingredients, c.tags)

            if f.is_soup:
                soups.append(c)
                continue

            if f.is_staple:
                staples.append(c)
                continue

            # 非汤非主食：根据蛋白倾向划分主菜/配菜
            if f.is_protein:
                mains.append(c)
            else:
                sides.append(c)

        # 排序策略：更“家常/清淡/川湘”等由外层提前排序；这里按可用性与简单倾向
        main_pool = mains if prefer_protein else sides
        fallback_pool = sides if prefer_protein else mains
        main = self._pick_one(main_pool, used_names) or self._pick_one(fallback_pool, used_names) or (candidates[0] if candidates else None)
        if main is None:
            raise ValueError("No candidates to compose mealset")

        used_names.add(main.meal.name)

        side = self._pick_one(sides, used_names) if want_side else None
        if side:
            used_names.add(side.meal.name)

        staple = self._pick_one(staples, used_names) if want_staple else None
        if staple:
            used_names.add(staple.meal.name)

        soup = self._pick_one(soups, used_names) if want_soup else None
        if soup:
            used_names.add(soup.meal.name)

        return MealSet(
            main=main.meal,
            side=side.meal if side else None,
            staple=staple.meal if staple else None,
            soup=soup.meal if soup else None,
        )
