# skills/meal_replace.py
from __future__ import annotations

from typing import Dict, List, Optional, Set

from models import Meal
from skills.meal_classifier import MealClassifierSkill


class MealReplaceSkill:
    """
    动态替换某一餐的某个部分（主菜/配菜/主食/汤）。
    用户说"晚餐换个清淡的"或"把今天午餐的主菜换成清蒸鱼"
    系统能针对性地从菜谱库里重新选菜，而不是全部重新生成。
    """

    def __init__(self):
        self.classifier = MealClassifierSkill()

    def replace_meal_part(
            self,
            recipe_db: List[Meal],
            recipe_meta: Dict[str, dict],
            part_type: str,  # "main" | "side" | "staple" | "soup"
            constraint: Optional[str],  # "清淡的" | "蒸" | "鱼" 等自然语言约束
            avoid: Optional[List[str]],  # 忌口食材
            used_names: Set[str],  # 已经用过的菜名（避免重复）
    ) -> Optional[Meal]:
        """
        从菜谱库里找一道符合条件的菜，返回 Meal。
        失败则返回 None。
        """

        # 第1步：按 part_type 初筛菜品
        candidates: List[Meal] = []

        for meal in recipe_db:
            if meal.name in used_names:
                continue

            features = self.classifier.classify(
                meal.name,
                meal.ingredients,
                recipe_meta.get(meal.name, {})
            )

            if part_type == "main" and features.is_protein:
                candidates.append(meal)
            elif part_type == "side" and features.is_veg and not features.is_protein:
                candidates.append(meal)
            elif part_type == "staple" and features.is_staple:
                candidates.append(meal)
            elif part_type == "soup" and features.is_soup:
                candidates.append(meal)

        if not candidates:
            return None

        # 第2步：按 avoid（忌口）二次过滤
        if avoid:
            avoid_set = set(avoid)
            candidates = [
                m for m in candidates
                if not any(ing in avoid_set for ing in m.ingredients.keys())
            ]

        if not candidates:
            return None

        # 第3步：按 constraint 排序（偏好匹配）
        def score_constraint(meal: Meal) -> int:
            if not constraint:
                return 0

            name = meal.name
            tags = recipe_meta.get(name, {})
            s = 0

            # 处理"清淡/清蒸/白灼"类约束
            if any(k in constraint for k in ["清淡", "清蒸", "白灼"]):
                style = set(tags.get("style", []))
                if "清淡" in style:
                    s += 10
                # 检查烹饪方法
                methods = set(tags.get("method", []))
                if methods & {"蒸", "煮", "拌"}:
                    s += 5

            # 处理食材约束（鱼、肉等）
            if "鱼" in constraint:
                if any(k in name for k in ["鱼", "虾", "蟹", "贝"]):
                    s += 10
            if "肉" in constraint:
                if any(k in name for k in ["鸡", "牛", "羊", "猪", "肉"]):
                    s += 10
            if "蔬菜" in constraint or "素" in constraint:
                features = self.classifier.classify(name, meal.ingredients, tags)
                if features.is_veg and not features.is_protein:
                    s += 10

            # 处理烹饪方法约束
            if "炒" in constraint:
                methods = set(tags.get("method", []))
                if "炒" in methods:
                    s += 5
            if "炖" in constraint:
                methods = set(tags.get("method", []))
                if "炖" in methods:
                    s += 5
            if "红烧" in constraint:
                methods = set(tags.get("method", []))
                if "红烧" in methods:
                    s += 5

            return s

        scored = [(score_constraint(m), m) for m in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        # 返回评分最高的菜
        return scored[0][1] if scored else None