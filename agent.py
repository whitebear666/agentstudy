# agent.py
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from models import UserPrefs, Meal, DayPlan, MealSet
from tools import ReadJsonTool, WriteJsonTool, WriteTextTool
from skills.meal_composer import MealComposerSkill, CandidateMeal


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
            name = obj.get("name")
            ingredients = obj.get("ingredients")
            steps = obj.get("steps")

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
                ing2[k.strip()] = str(v).strip() if v is not None else "适量/按需"
            if not ing2:
                continue

            steps2 = [str(s).strip() for s in steps if str(s).strip()]
            if not steps2:
                continue

            nm = name.strip()
            meals.append(Meal(name=nm, ingredients=ing2, steps=steps2))
            meta[nm] = _get_tags(obj)

        return meals, meta

    def _filter_recipes(self, avoid: List[str] | None) -> List[Meal]:
        if not avoid:
            return self.recipe_db
        avoid_set = set(avoid)
        ok = []
        for r in self.recipe_db:
            if any(item in avoid_set for item in r.ingredients.keys()):
                continue
            ok.append(r)
        return ok

    def _prefer_by_tags(self, meals: List[Meal], prefs: UserPrefs) -> List[Meal]:
        cuisine = (prefs.cuisine or "").strip()

        def score(meal: Meal) -> int:
            tags = self.recipe_meta.get(meal.name, {})
            styles = set(_tag_list(tags, "style"))
            spicy = _tag_str(tags, "spicy")
            methods = set(_tag_list(tags, "method"))

            s = 0
            if "清淡" in cuisine:
                if "清淡" in styles:
                    s += 6
                if spicy in ("none", "mild"):
                    s += 3
                if methods & {"蒸", "煮", "拌"}:
                    s += 1

            if ("川" in cuisine) or ("辣" in cuisine) or ("微辣" in cuisine):
                if "川湘" in styles:
                    s += 6
                if spicy in ("medium", "hot"):
                    s += 3

            if "家常" in cuisine:
                if "家常" in styles:
                    s += 3

            return s

        scored = [(score(m), m) for m in meals]
        if all(s == 0 for s, _ in scored):
            return meals

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

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

    def plan(self, prefs: UserPrefs, fridge_path: str = "data/fridge.json") -> Tuple[List[DayPlan], Dict[str, str]]:
        fridge = {}
        try:
            fridge = self.read_json.run(fridge_path)
        except Exception:
            fridge = {}

        meals = self._filter_recipes(prefs.avoid)
        if not meals:
            meals = DEFAULT_RECIPE_DB

        meals = self._prefer_by_tags(meals, prefs)

        breakfast_pool = self._pool(meals, "breakfast")
        main_pool = self._pool(meals, "dinner")  # 午晚餐都用正餐池

        # 取前 N 做候选，既贴近偏好又保多样性
        bf_candidates = self._as_candidates(breakfast_pool[: min(len(breakfast_pool), 260)])
        main_candidates = self._as_candidates(main_pool[: min(len(main_pool), 520)])

        day_plans: List[DayPlan] = []
        used_names: set[str] = set()

        for i in range(prefs.days):
            # 早餐：一般也给主食；汤可选（粥/汤本身也会被 classifier 当 soup/staple）
            breakfast = self.composer.compose_mealset(
                prefs=prefs,
                candidates=bf_candidates,
                used_names=used_names,
                want_soup=False,
                want_staple=True,
            )

            lunch = self.composer.compose_mealset(
                prefs=prefs,
                candidates=main_candidates,
                used_names=used_names,
                want_soup=True,
                want_staple=True,
            )

            dinner = self.composer.compose_mealset(
                prefs=prefs,
                candidates=main_candidates,
                used_names=used_names,
                want_soup=True,
                want_staple=True,
            )

            day_plans.append(DayPlan(day_index=i + 1, breakfast=breakfast, lunch=lunch, dinner=dinner))

        # 合并购物清单（仍然 MVP：不累加数量）
        need: Dict[str, str] = {}

        try:
            have_all = sum((fridge.get(cat, []) for cat in fridge.keys()), [])
        except Exception:
            have_all = []

        def add_mealset(ms: MealSet) -> None:
            for meal in [ms.main, ms.side, ms.staple, ms.soup]:
                if not meal:
                    continue
                for k, v in meal.ingredients.items():
                    if k in have_all:
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
        lines.append(f"- 忌口/过敏：{', '.join(prefs.avoid) if prefs.avoid else '无'}")
        lines.append("")

        def render_mealset(title: str, ms: MealSet) -> None:
            lines.append(f"### {title}")
            for part_name, meal in [("主菜", ms.main), ("配菜", ms.side), ("主食", ms.staple), ("汤", ms.soup)]:
                if not meal:
                    continue
                lines.append(f"#### {part_name}：{meal.name}")

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
                for s in meal.steps[:12]:
                    lines.append(f"  1. {s}")
                if len(meal.steps) > 12:
                    lines.append("  1. （步骤较长，已省略部分…）")
                lines.append("")

        for dp in plans:
            lines.append(f"## Day {dp.day_index}")
            render_mealset("早餐", dp.breakfast)
            render_mealset("午餐", dp.lunch)
            render_mealset("晚餐", dp.dinner)

        return "\n".join(lines)

    def run(self, prefs: UserPrefs) -> None:
        plans, shopping = self.plan(prefs)
        md = self.render_markdown(prefs, plans)
        self.write_text.run("output/meal_plan.md", md)
        self.write_json.run("output/shopping_list.json", shopping)