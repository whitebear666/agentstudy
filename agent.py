"""菜单生成核心模块。

作用：
    读取菜谱数据，根据用户偏好生成多天早/中/晚餐计划，并输出
    meal_plan.md、shopping_list.json、prefs.json 等结果文件。

关联模块：
    models.py 提供 UserPrefs、Meal、MealSet、DayPlan。
    tools.py 负责 JSON/文本文件读写。
    skills/meal_composer.py 负责从候选菜中组合一餐。
    skills/cooking_profile.py 负责难度、预计时间、评分和时间线。
    agent_controller.py 在聊天 UI 中调用本模块完成生成。
"""

# agent.py
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple, Optional

from models import UserPrefs, Meal, DayPlan, MealSet
from tools import ReadJsonTool, WriteJsonTool, WriteTextTool
from skills.meal_composer import MealComposerSkill, CandidateMeal
from skills.cooking_profile import build_mealset_timeline, build_recipe_meta, mealset_total_time, stars
from skills.recipe_quality import clean_recipe_object, pantry_expiry_priority, pantry_match_score

DEFAULT_RECIPE_DB = [
    Meal(
        name="西红柿炒蛋",
        ingredients={"鸡蛋": "3个", "西红柿": "2个", "葱": "少许"},
        steps=["西红柿切块，鸡蛋打散。", "热锅下油炒鸡蛋盛出。", "炒西红柿出汁，回锅鸡蛋，加盐调味。"],
    ),
    Meal(
        name="土豆炖鸡胸",
        ingredients={"鸡胸肉": "300g", "土豆": "2个", "姜": "2片", "蒜": "2瓣"},
        steps=["鸡胸切块焯水。", "土豆切块。", "下姜蒜炒香，加入鸡胸和土豆，加水炖至软烂。"],
    ),
]


def _get_tags(obj: dict) -> dict:
    tags = obj.get("tags")
    return tags if isinstance(tags, dict) else {}


def _tag_list(tags: dict, key: str) -> List[str]:
    v = tags.get(key, [])
    if isinstance(v, list):
        return [str(x) for x in v]
    return []


def _tag_str(tags: dict, key: str) -> str:
    v = tags.get(key)
    return str(v) if isinstance(v, str) else ""


def _is_valid_ingredient_name(name: str) -> bool:
    value = name.strip()
    if not value:
        return False
    if value in {"*", "-", "?", "!", ".", "。"}:
        return False
    if value.rstrip(".").isdigit():
        return False
    if len(value) > 40:
        return False
    noisy_tokens = ("注意", "材料都是", "步骤", "做法", "难度", "卡路里")
    return not any(token in value for token in noisy_tokens)


def _shopping_categories(shopping: Dict[str, str]) -> Dict[str, List[str]]:
    categories: Dict[str, List[str]] = {
        "vegetables": [],
        "protein": [],
        "staples": [],
        "seasonings": [],
        "other": [],
    }
    rules = {
        "vegetables": ("菜", "瓜", "豆角", "土豆", "番茄", "西红柿", "葱", "姜", "蒜", "椒", "蘑菇", "菇"),
        "protein": ("肉", "鸡", "蛋", "鱼", "虾", "牛", "羊", "猪", "豆腐"),
        "staples": ("米", "面", "饭", "粉", "饼", "馒头", "粥"),
        "seasonings": ("盐", "糖", "油", "酱", "醋", "料酒", "蚝油", "味精", "胡椒"),
    }
    for ingredient in shopping:
        target = "other"
        for category, keywords in rules.items():
            if any(keyword in ingredient for keyword in keywords):
                target = category
                break
        categories[target].append(ingredient)
    return {key: value for key, value in categories.items() if value}


def _shopping_payload(shopping: Dict[str, str]) -> Dict[str, Any]:
    return {
        "items": shopping,
        "categories": _shopping_categories(shopping),
    }


def _stock_names(fridge: Any, pantry: Any) -> List[str]:
    names: List[str] = []
    if isinstance(fridge, dict):
        for value in fridge.values():
            if isinstance(value, list):
                names.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, dict):
                names.extend(str(item).strip() for item in value.keys() if str(item).strip())
    if isinstance(pantry, dict):
        names.extend(str(name).strip() for name in pantry.keys() if str(name).strip())
    return list(dict.fromkeys(names))


def _stock_priority(fridge: Any, pantry: Any) -> Dict[str, int]:
    priority = pantry_expiry_priority(pantry)
    if isinstance(fridge, dict):
        for name in _stock_names(fridge, {}):
            priority.setdefault(name, 2)
    return priority


def _is_in_stock(ingredient: str, stock_names: List[str]) -> bool:
    return any(item == ingredient or item in ingredient or ingredient in item for item in stock_names)


def _is_recipe_meta_step(text: str) -> bool:
    return any(token in text for token in ["预估烹饪难度", "预估卡路里", "预计卡路里"])


class GroceryMealAgent:
    def __init__(self, seed: int | None = None):
        self.read_json = ReadJsonTool()
        self.write_json = WriteJsonTool()
        self.write_text = WriteTextTool()

        self._rng = random.Random(seed)

        self.recipe_db: List[Meal] = []
        self.recipe_meta: Dict[str, dict] = {}

        self._load_recipes_with_fallback(
            primary_path="data/recipes_tagged.json",
            fallback_path="data/recipes.json",
        )

        self.composer = MealComposerSkill()

    def _load_recipes_with_fallback(self, primary_path: str, fallback_path: str) -> None:
        try:
            raw = self.read_json.run(primary_path)
            meals, meta = self._parse_recipes_with_meta(raw)
            if meals:
                self.recipe_db, self.recipe_meta = meals, meta
                return
        except Exception:
            pass

        try:
            raw = self.read_json.run(fallback_path)
            meals, meta = self._parse_recipes_with_meta(raw)
            if meals:
                self.recipe_db, self.recipe_meta = meals, meta
                return
        except Exception:
            pass

        self.recipe_db = DEFAULT_RECIPE_DB
        self.recipe_meta = {m.name: {} for m in DEFAULT_RECIPE_DB}

    def _parse_recipes_with_meta(self, raw: Any) -> Tuple[List[Meal], Dict[str, dict]]:
        if not isinstance(raw, list):
            raise ValueError("recipes json must be a list")

        meals: List[Meal] = []
        meta: Dict[str, dict] = {}

        for obj in raw:
            if not isinstance(obj, dict):
                continue
            cleaned = clean_recipe_object(obj)
            if not cleaned:
                continue
            name = cleaned.get("name")
            ingredients = cleaned.get("ingredients")
            steps = cleaned.get("steps")

            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(ingredients, dict) or not ingredients:
                continue
            if not isinstance(steps, list) or not steps:
                continue

            ing2: Dict[str, str] = {}
            for k, v in ingredients.items():
                if not isinstance(k, str) or not k.strip():
                    continue
                ingredient_name = k.strip()
                if not _is_valid_ingredient_name(ingredient_name):
                    continue
                ing2[ingredient_name] = str(v).strip() if v is not None else "适量/按需"
            if not ing2:
                continue

            steps2 = [str(s).strip() for s in steps if str(s).strip()]
            if not steps2:
                continue

            nm = name.strip()
            tags = _get_tags(cleaned)
            meals.append(Meal(name=nm, ingredients=ing2, steps=steps2, meta=build_recipe_meta(nm, steps2, tags)))
            meta[nm] = tags

        return meals, meta

    def _filter_recipes(self, avoid: List[str] | None) -> List[Meal]:
        if not avoid:
            return self.recipe_db
        avoid_terms = [item.strip() for item in avoid if str(item).strip()]
        ok = []
        for r in self.recipe_db:
            if any(term in r.name for term in avoid_terms):
                continue
            if any(any(term in ingredient for term in avoid_terms) for ingredient in r.ingredients.keys()):
                continue
            ok.append(r)
        return ok

    def _prefer_by_style(self, meals: List[Meal], style: Optional[str]) -> List[Meal]:
        """
        通用偏好排序：根据 style 字符串排序菜品。
        style 可以是 None / "清淡" / "川菜" / "家常" / "微辣" 等任意字符串。
        """
        if not style:
            return meals

        style_str = (style or "").strip()

        def score(meal: Meal) -> int:
            tags = self.recipe_meta.get(meal.name, {})
            styles = set(_tag_list(tags, "style"))
            spicy = _tag_str(tags, "spicy")
            methods = set(_tag_list(tags, "method"))

            s = 0
            if "清淡" in style_str:
                if "清淡" in styles:
                    s += 6
                if spicy in ("none", "mild"):
                    s += 3
                if methods & {"蒸", "煮", "拌"}:
                    s += 1

            if ("川" in style_str) or ("辣" in style_str) or ("微辣" in style_str):
                if "川湘" in styles:
                    s += 6
                if spicy in ("medium", "hot"):
                    s += 3

            if "家常" in style_str:
                if "家常" in styles:
                    s += 3

            return s

        scored = [(score(m), m) for m in meals]
        if all(s == 0 for s, _ in scored):
            return meals

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _prefer_favorites(self, meals: List[Meal], favorites: Optional[List[str]]) -> List[Meal]:
        if not favorites:
            return meals
        favorite_terms = [item.strip() for item in favorites if str(item).strip()]
        if not favorite_terms:
            return meals

        def score(meal: Meal) -> int:
            return max((10 if term == meal.name else 6 if term in meal.name or meal.name in term else 0) for term in favorite_terms)

        return sorted(meals, key=score, reverse=True)

    def _prefer_by_health_goal(self, meals: List[Meal], goal: Optional[str]) -> List[Meal]:
        if not goal:
            return meals
        goal = goal.strip()

        def score(meal: Meal) -> int:
            tags = self.recipe_meta.get(meal.name, {})
            methods = set(_tag_list(tags, "method"))
            text = meal.name + " " + " ".join(meal.ingredients.keys())
            s = 0
            if "减脂" in goal or "控糖" in goal or "少油" in goal:
                if methods & {"蒸", "煮", "拌", "白灼"}:
                    s += 5
                if methods & {"炸", "煎", "红烧"}:
                    s -= 4
                if any(word in text for word in ["蔬菜", "青菜", "白菜", "西兰花", "豆腐", "鱼"]):
                    s += 2
            if "增肌" in goal or "高蛋白" in goal:
                if any(word in text for word in ["鸡", "鱼", "虾", "牛肉", "鸡蛋", "豆腐"]):
                    s += 5
            return s

        return sorted(meals, key=score, reverse=True)

    def _prefer_by_stock(self, meals: List[Meal], stock_priority: Dict[str, int]) -> List[Meal]:
        if not stock_priority:
            return meals
        return sorted(
            meals,
            key=lambda meal: pantry_match_score(meal.ingredients.keys(), stock_priority),
            reverse=True,
        )

    def _pool(self, meals: List[Meal], meal_type: str) -> List[Meal]:
        # 用 tags.meal_type 分池；没有 tags 就返回全量（不强依赖）
        pool = []
        for m in meals:
            tags = self.recipe_meta.get(m.name, {})
            types = set(_tag_list(tags, "meal_type"))
            if types and meal_type in types:
                pool.append(m)
        return pool or meals

    def _as_candidates(self, meals: List[Meal]) -> List[CandidateMeal]:
        return [CandidateMeal(meal=m, tags=self.recipe_meta.get(m.name, {})) for m in meals]

    def _meal_shape(self, prefs: UserPrefs, meal_type: str) -> Dict[str, bool]:
        """把用户的一餐几道菜、几荤几素偏好映射到现有 MealSet 槽位。"""
        if meal_type == "breakfast":
            return {
                "want_side": False,
                "want_soup": False,
                "want_staple": True,
                "prefer_protein": prefs.meat_count != 0,
            }

        dish_count = prefs.dish_count if prefs.dish_count is not None else 3
        vegetable_count = prefs.vegetable_count
        meat_count = prefs.meat_count

        want_side = dish_count >= 2 or (vegetable_count is not None and vegetable_count >= 1)
        want_soup = dish_count >= 3
        want_staple = True
        prefer_protein = meat_count != 0

        if vegetable_count == 0:
            want_side = False
        if dish_count <= 1:
            want_side = False
            want_soup = False
        elif dish_count == 2:
            want_soup = False

        return {
            "want_side": want_side,
            "want_soup": want_soup,
            "want_staple": want_staple,
            "prefer_protein": prefer_protein,
        }

    def plan(self, prefs: UserPrefs, fridge_path: str = "data/fridge.json") -> Tuple[List[DayPlan], Dict[str, str]]:
        fridge = {}
        pantry = {}
        try:
            fridge = self.read_json.run(fridge_path)
        except Exception:
            fridge = {}
        try:
            pantry = self.read_json.run("data/pantry.json")
        except Exception:
            pantry = {}

        meals = self._filter_recipes(prefs.avoid)
        if not meals:
            meals = DEFAULT_RECIPE_DB

        stock_priority = _stock_priority(fridge, pantry)

        # 每一餐用自己的 style，如果没有则回退到全局 cuisine
        breakfast_style = prefs.breakfast_style or prefs.cuisine
        lunch_style = prefs.lunch_style or prefs.cuisine
        dinner_style = prefs.dinner_style or prefs.cuisine

        # 分别排序：餐次风格、健康目标、库存临期命中、收藏偏好逐层加权。
        meals_breakfast = self._prefer_favorites(
            self._prefer_by_stock(
                self._prefer_by_health_goal(self._prefer_by_style(meals, breakfast_style), prefs.health_goal),
                stock_priority,
            ),
            prefs.favorite_recipes,
        )
        meals_lunch = self._prefer_favorites(
            self._prefer_by_stock(
                self._prefer_by_health_goal(self._prefer_by_style(meals, lunch_style), prefs.health_goal),
                stock_priority,
            ),
            prefs.favorite_recipes,
        )
        meals_dinner = self._prefer_favorites(
            self._prefer_by_stock(
                self._prefer_by_health_goal(self._prefer_by_style(meals, dinner_style), prefs.health_goal),
                stock_priority,
            ),
            prefs.favorite_recipes,
        )

        # 再分池（按 meal_type 标签）
        breakfast_pool = self._pool(meals_breakfast, "breakfast")
        lunch_pool = self._pool(meals_lunch, "dinner")  # lunch 也用"正餐"标签池
        dinner_pool = self._pool(meals_dinner, "dinner")

        # 取前 N 做候选，既贴近偏好又保多样性
        bf_candidates = self._as_candidates(breakfast_pool[: min(len(breakfast_pool), 260)])
        lunch_candidates = self._as_candidates(lunch_pool[: min(len(lunch_pool), 520)])
        dinner_candidates = self._as_candidates(dinner_pool[: min(len(dinner_pool), 520)])

        day_plans: List[DayPlan] = []
        used_names: set[str] = set()
        breakfast_shape = self._meal_shape(prefs, "breakfast")
        lunch_shape = self._meal_shape(prefs, "lunch")
        dinner_shape = self._meal_shape(prefs, "dinner")

        for i in range(prefs.days):
            # 早餐：一般也给主食；汤可选（粥/汤本身也会被 classifier 当 soup/staple）
            breakfast = self.composer.compose_mealset(
                prefs=prefs,
                candidates=bf_candidates,
                used_names=used_names,
                **breakfast_shape,
            )

            lunch = self.composer.compose_mealset(
                prefs=prefs,
                candidates=lunch_candidates,
                used_names=used_names,
                **lunch_shape,
            )

            dinner = self.composer.compose_mealset(
                prefs=prefs,
                candidates=dinner_candidates,
                used_names=used_names,
                **dinner_shape,
            )

            day_plans.append(DayPlan(day_index=i + 1, breakfast=breakfast, lunch=lunch, dinner=dinner))

        # 合并购物清单（仍然 MVP：不累加数量）
        need: Dict[str, str] = {}

        try:
            have_all = _stock_names(fridge, pantry)
        except Exception:
            have_all = []

        def add_mealset(ms: MealSet) -> None:
            for meal in [ms.main, ms.side, ms.staple, ms.soup]:
                if not meal:
                    continue
                for k, v in meal.ingredients.items():
                    if _is_in_stock(k, have_all):
                        continue
                    if not _is_valid_ingredient_name(k):
                        continue
                    need[k] = "适量/按需"

        for dp in day_plans:
            add_mealset(dp.breakfast)
            add_mealset(dp.lunch)
            add_mealset(dp.dinner)

        return day_plans, need

    def render_markdown(self, prefs: UserPrefs, plans: List[DayPlan]) -> str:
        lines: List[str] = []
        lines.append(f"# {prefs.days} 天食谱规划（{prefs.people}人）")
        lines.append("")
        lines.append("## 偏好/约束")
        lines.append(f"- 人数：{prefs.people}")
        lines.append(f"- 天数：{prefs.days}")
        lines.append(f"- 菜系：{prefs.cuisine}")
        if prefs.dish_count is not None:
            lines.append(f"- 每餐菜数：{prefs.dish_count} 道")
        if prefs.meat_count is not None or prefs.vegetable_count is not None:
            meat = prefs.meat_count if prefs.meat_count is not None else "未指定"
            vegetable = prefs.vegetable_count if prefs.vegetable_count is not None else "未指定"
            lines.append(f"- 荤素搭配：{meat} 荤 / {vegetable} 素")
        if prefs.breakfast_style:
            lines.append(f"- 早餐偏好：{prefs.breakfast_style}")
        if prefs.lunch_style:
            lines.append(f"- 午餐偏好：{prefs.lunch_style}")
        if prefs.dinner_style:
            lines.append(f"- 晚餐偏好：{prefs.dinner_style}")
        lines.append(f"- 忌口/过敏：{', '.join(prefs.avoid) if prefs.avoid else '无'}")
        lines.append("")

        def render_mealset(title: str, ms: MealSet) -> None:
            lines.append(f"### {title}")
            total_time = mealset_total_time(ms)
            if total_time:
                lines.append(f"- 本餐预计耗时：约 {total_time} 分钟")
                timeline = build_mealset_timeline(ms)
                if timeline:
                    lines.append("- 建议时间规划：")
                    for item in timeline:
                        lines.append(f"  - T+{item.offset_minutes} 分钟：{item.title}")
                lines.append("")

            for part_name, meal in [("主菜", ms.main), ("配菜", ms.side), ("主食", ms.staple), ("汤", ms.soup)]:
                if not meal:
                    continue
                lines.append(f"#### {part_name}：{meal.name}")
                if meal.meta:
                    difficulty = stars(meal.meta.difficulty)
                    cook_time = meal.meta.cook_time_minutes or 25
                    score = meal.meta.score or 4.0
                    source_label = "原文提取" if meal.meta.time_source == "parsed" else "规则估算"
                    lines.append(f"- 难度：{difficulty}（{meal.meta.difficulty or 1}/5）")
                    lines.append(f"- 预计时间：约 {cook_time} 分钟（{source_label}）")
                    lines.append(f"- 推荐评分：{score:.1f}/5")

                tags = self.recipe_meta.get(meal.name, {})
                if tags:
                    styles = ",".join(_tag_list(tags, "style"))
                    methods = ",".join(_tag_list(tags, "method"))
                    spicy = _tag_str(tags, "spicy") or "unknown"
                    extra = []
                    if styles:
                        extra.append(f"风格:{styles}")
                    if methods:
                        extra.append(f"做法:{methods}")
                    if spicy:
                        extra.append(f"辣度:{spicy}")
                    if extra:
                        lines.append(f"- 标签：{' | '.join(extra)}")

                lines.append("- 食材：")
                for ing, qty in meal.ingredients.items():
                    lines.append(f"  - {ing}：{qty}")
                lines.append("- 步骤：")
                visible_steps = [s for s in meal.steps if not _is_recipe_meta_step(s)]
                for s in visible_steps[:12]:
                    lines.append(f"  1. {s}")
                if len(visible_steps) > 12:
                    lines.append("  1. （步骤较长，已省略部分…）")
                lines.append("")

        for dp in plans:
            lines.append(f"## Day {dp.day_index}")
            render_mealset("早餐", dp.breakfast)
            render_mealset("午餐", dp.lunch)
            render_mealset("晚餐", dp.dinner)

        return "\n".join(lines)

    def show_current_menu(self, day_plans: List[DayPlan]) -> str:
        """
        生成当前菜单的文本表示，供用户查看和决定替换哪一餐。
        """
        if not day_plans:
            return "暂无生成的菜单。"

        lines = ["# 当前菜单规划\n"]
        for plan in day_plans:
            lines.append(f"## 第 {plan.day_index} 天")

            # 早餐
            breakfast_main = plan.breakfast.main.name if plan.breakfast.main else "无"
            lines.append(f"- **早餐**：{breakfast_main}")

            # 午餐
            lunch_main = plan.lunch.main.name if plan.lunch.main else "无"
            lines.append(f"- **午餐**：{lunch_main}")

            # 晚餐
            dinner_main = plan.dinner.main.name if plan.dinner.main else "无"
            lines.append(f"- **晚餐**：{dinner_main}")
            lines.append("")

        return "\n".join(lines)

    def run(self, prefs: UserPrefs, save_output: bool = True) -> Tuple[List[DayPlan], Dict[str, str]]:
        """
        执行菜单规划。

        参数:
            prefs: 用户偏好
            save_output: 是否保存文件到 output/ 目录

        返回:
            (day_plans, shopping_list): 生成的菜单计划和购物清单
        """
        plans, shopping = self.plan(prefs)

        if save_output:
            md = self.render_markdown(prefs, plans)
            self.write_text.run("output/meal_plan.md", md)
            self.write_json.run("output/shopping_list.json", _shopping_payload(shopping))

            # 修复：手动构建 prefs 字典，因为 UserPrefs 是 dataclass 不是 Pydantic
            prefs_dict = {
                "people": prefs.people,
                "days": prefs.days,
                "budget": prefs.budget,
                "avoid": prefs.avoid,
                "cuisine": prefs.cuisine,
                "has_kitchen": prefs.has_kitchen,
                "dish_count": prefs.dish_count,
                "meat_count": prefs.meat_count,
                "vegetable_count": prefs.vegetable_count,
                "breakfast_style": prefs.breakfast_style,
                "lunch_style": prefs.lunch_style,
                "dinner_style": prefs.dinner_style,
                "health_goal": prefs.health_goal,
                "favorite_recipes": prefs.favorite_recipes,
            }
            self.write_json.run("output/prefs.json", prefs_dict)

        return plans, shopping
