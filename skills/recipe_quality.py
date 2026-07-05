"""Recipe cleanup and lightweight quality enrichment.

Role:
    Normalizes recipe data imported from open-source datasets, removes noisy
    ingredients/steps, infers extra tags, and scores pantry matches.

Related modules:
    scripts/tag_recipes.py uses this module when rebuilding recipes_tagged.json.
    agent.py uses this module while loading recipes and ranking pantry-friendly
    candidates.
    skills/cooking_profile.py consumes cleaned steps and inferred method tags.
"""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


NOISY_STEP_TOKENS = (
    "![",
    "http://",
    "https://",
    "预估烹饪难度",
    "预估卡路里",
    "预计卡路里",
    "小贴士",
)

NOISY_INGREDIENT_TOKENS = (
    "步骤",
    "做法",
    "注意",
    "材料都是",
    "难度",
    "卡路里",
    "tips",
)

METHOD_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "炒": ("炒", "爆炒", "快炒", "煸"),
    "煎": ("煎", "香煎"),
    "炖": ("炖", "焖", "煨", "红烧"),
    "煮": ("煮", "水煮", "汆", "汤", "粥"),
    "蒸": ("蒸", "清蒸"),
    "烤": ("烤", "焗"),
    "拌": ("拌", "凉拌"),
    "炸": ("炸", "油炸"),
    "白灼": ("白灼",),
}

PROTEIN_KEYWORDS = ("鸡", "鸭", "鱼", "虾", "牛", "羊", "猪", "肉", "蛋", "豆腐", "贝")
VEGETABLE_KEYWORDS = ("菜", "瓜", "菇", "笋", "豆角", "土豆", "番茄", "西红柿", "茄子", "菠菜", "白菜")
STAPLE_KEYWORDS = ("米", "面", "粉", "饭", "粥", "馒头", "饼", "吐司", "意面")


def normalize_recipe_name(name: str) -> str:
    value = re.sub(r"\s+", "", str(name or "").strip())
    value = re.sub(r"^[#\-\*\d\.\s、]+", "", value)
    return value[:60]


def normalize_ingredient_name(name: str) -> str:
    value = str(name or "").strip()
    value = re.sub(r"^[\-\*\d\.\s、]+", "", value)
    value = re.sub(r"[：:，,。；;]+$", "", value).strip()
    return value


def is_valid_ingredient_name(name: str) -> bool:
    value = normalize_ingredient_name(name)
    if not value or len(value) > 32:
        return False
    if value.rstrip(".").isdigit():
        return False
    if value in {"*", "-", "?", "!", ".", "、"}:
        return False
    return not any(token.lower() in value.lower() for token in NOISY_INGREDIENT_TOKENS)


def clean_ingredients(ingredients: Any) -> Dict[str, str]:
    if not isinstance(ingredients, dict):
        return {}
    cleaned: Dict[str, str] = {}
    for raw_name, raw_qty in ingredients.items():
        name = normalize_ingredient_name(raw_name)
        if not is_valid_ingredient_name(name):
            continue
        qty = str(raw_qty).strip() if raw_qty is not None else ""
        cleaned[name] = qty or "适量/按需"
    return cleaned


def clean_steps(steps: Any) -> List[str]:
    if not isinstance(steps, list):
        return []
    cleaned: List[str] = []
    seen: set[str] = set()
    for raw in steps:
        step = str(raw or "").strip()
        step = re.sub(r"^\d+[\.\)、\s]+", "", step)
        step = re.sub(r"\s+", " ", step).strip()
        if not step:
            continue
        if any(token in step for token in NOISY_STEP_TOKENS):
            continue
        if len(step) > 180:
            continue
        if step in seen:
            continue
        seen.add(step)
        cleaned.append(step)
    return cleaned


def _ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def infer_quality_tags(name: str, ingredients: Dict[str, str], steps: List[str], tags: Optional[dict] = None) -> dict:
    tags = dict(tags or {})
    text = " ".join([name, *ingredients.keys(), *steps])

    methods = set(_ensure_list(tags.get("method")))
    for method, keywords in METHOD_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            methods.add(method)
    if methods:
        tags["method"] = sorted(methods)

    meal_types = set(_ensure_list(tags.get("meal_type")))
    if any(keyword in text for keyword in STAPLE_KEYWORDS):
        meal_types.add("breakfast")
    meal_types.update({"lunch", "dinner"})
    tags["meal_type"] = sorted(meal_types)

    styles = set(_ensure_list(tags.get("style")))
    if any(method in methods for method in ("蒸", "煮", "拌", "白灼")):
        styles.add("清淡")
    styles.add("家常")
    tags["style"] = sorted(styles)

    if any(keyword in text for keyword in ("麻辣", "香辣", "辣椒", "干锅", "水煮")):
        tags["spicy"] = tags.get("spicy") if tags.get("spicy") in {"hot", "medium"} else "medium"
    elif any(keyword in text for keyword in ("清蒸", "白灼", "清淡")):
        tags["spicy"] = "none"
    else:
        tags.setdefault("spicy", "unknown")

    tags["is_soup"] = bool(tags.get("is_soup")) or any(keyword in name for keyword in ("汤", "羹", "粥"))
    tags["protein_level"] = "high" if any(keyword in text for keyword in PROTEIN_KEYWORDS) else "normal"
    tags["vegetable_forward"] = any(keyword in text for keyword in VEGETABLE_KEYWORDS)
    return tags


def clean_recipe_object(obj: dict) -> Optional[dict]:
    if not isinstance(obj, dict):
        return None
    name = normalize_recipe_name(str(obj.get("name", "")))
    ingredients = clean_ingredients(obj.get("ingredients"))
    steps = clean_steps(obj.get("steps"))
    if not name or not ingredients or not steps:
        return None
    cleaned = dict(obj)
    cleaned["name"] = name
    cleaned["ingredients"] = ingredients
    cleaned["steps"] = steps
    cleaned["tags"] = infer_quality_tags(name, ingredients, steps, obj.get("tags") if isinstance(obj.get("tags"), dict) else {})
    return cleaned


def pantry_expiry_priority(pantry: Any, today: Optional[date] = None) -> Dict[str, int]:
    if not isinstance(pantry, dict):
        return {}
    today = today or date.today()
    priorities: Dict[str, int] = {}
    for name, raw in pantry.items():
        key = str(name).strip()
        if not key:
            continue
        priority = 3
        expiry_value = raw.get("expiry_date") if isinstance(raw, dict) else None
        if expiry_value:
            try:
                expiry = datetime.fromisoformat(str(expiry_value)).date()
                days_left = (expiry - today).days
                if days_left < 0:
                    priority = 0
                elif days_left <= 3:
                    priority = 12
                elif days_left <= 7:
                    priority = 7
                else:
                    priority = 4
            except ValueError:
                priority = 3
        if priority:
            priorities[key] = priority
    return priorities


def pantry_match_score(ingredient_names: Iterable[str], pantry_priorities: Dict[str, int]) -> int:
    score = 0
    for ingredient in ingredient_names:
        for stock_name, priority in pantry_priorities.items():
            if stock_name == ingredient or stock_name in ingredient or ingredient in stock_name:
                score += priority
                break
    return score
