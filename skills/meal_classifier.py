# skills/meal_classifier.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class MealFeatures:
    is_staple: bool
    is_soup: bool
    is_protein: bool
    is_veg: bool


class MealClassifierSkill:
    """
    用菜名 + 食材名（以及可选 tags）做轻量分类。
    这是规则型 skill：稳定、可控、无模型成本。
    """

    STAPLE_NAME_KW = ["饭", "粥", "面", "粉", "馒头", "包子", "饼", "吐司", "三明治", "馄饨", "饺", "米线", "年糕"]
    SOUP_NAME_KW = ["汤", "羹", "锅", "煲"]  # 煲/锅不一定是汤，但先弱判断

    PROTEIN_ING_KW = [
        "鸡", "鸭", "鹅", "牛", "羊", "猪", "鱼", "虾", "蟹", "贝",
        "鸡蛋", "鸭蛋", "蛋", "牛奶", "奶", "豆腐", "豆干", "牛腩", "排骨", "鸡胸", "里脊"
    ]
    VEG_ING_KW = [
        "菜", "白菜", "生菜", "菠菜", "西兰花", "花菜", "黄瓜", "西红柿", "番茄", "土豆", "胡萝卜", "洋葱",
        "葱", "姜", "蒜", "香菇", "蘑菇", "青椒", "红椒", "茄子", "豆角", "芹菜"
    ]

    def classify(self, name: str, ingredients: Dict[str, str], tags: Dict | None = None) -> MealFeatures:
        tags = tags or {}

        n = name.strip()
        ing_names = list(ingredients.keys())

        is_staple = any(k in n for k in self.STAPLE_NAME_KW) or any(any(k in ing for k in ["米", "面"]) for ing in ing_names)
        is_soup = bool(tags.get("is_soup")) or any(k in n for k in self.SOUP_NAME_KW)

        is_protein = any(any(k in ing for k in self.PROTEIN_ING_KW) for ing in ing_names)
        is_veg = any(any(k in ing for k in self.VEG_ING_KW) for ing in ing_names)

        return MealFeatures(
            is_staple=is_staple,
            is_soup=is_soup,
            is_protein=is_protein,
            is_veg=is_veg,
        )