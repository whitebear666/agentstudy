# agent.py
from __future__ import annotations

import random
from typing import Dict, List, Tuple, Any

from models import UserPrefs, Meal, DayPlan
from tools import ReadJsonTool, WriteJsonTool, WriteTextTool


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
    Meal(
        name="葱油拌面",
        ingredients={"面条": "2人份", "葱": "1把", "酱油": "1-2勺"},
        steps=["煮面条过冷水。", "葱段小火煎出葱油。", "面条加酱油和葱油拌匀。"],
    ),
    Meal(
        name="蛋炒饭",
        ingredients={"大米": "2碗（熟饭）", "鸡蛋": "2个", "葱": "少许"},
        steps=["热锅下油炒鸡蛋。", "下熟饭翻炒。", "加盐/酱油调味，撒葱花。"],
    ),
]


class GroceryMealAgent:
    def __init__(self, recipes_path: str = "data/recipes.json", seed: int | None = None):
        self.read_json = ReadJsonTool()
        self.write_json = WriteJsonTool()
        self.write_text = WriteTextTool()

        self.recipes_path = recipes_path
        self.recipe_db: List[Meal] = self._load_recipes_or_default(recipes_path)

        # 允许固定 seed 便于复现（你也可以从 prefs.json 里带一个 seed）
        self._rng = random.Random(seed)

    def _load_recipes_or_default(self, path: str) -> List[Meal]:
        try:
            raw = self.read_json.run(path)
            meals = self._parse_recipes(raw)
            return meals or DEFAULT_RECIPE_DB
        except Exception:
            return DEFAULT_RECIPE_DB

    def _parse_recipes(self, raw: Any) -> List[Meal]:
        if not isinstance(raw, list):
            raise ValueError("recipes.json must be a list")

        meals: List[Meal] = []
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

            meals.append(Meal(name=name.strip(), ingredients=ing2, steps=steps2))
        return meals

    def _filter_recipes(self, avoid: List[str] | None) -> List[Meal]:
        db = self.recipe_db
        if not avoid:
            return db
        avoid_set = set(avoid)
        ok = []
        for r in db:
            # 简单规则：若“食材名”命中 avoid，则排除
            if any(item in avoid_set for item in r.ingredients.keys()):
                continue
            ok.append(r)
        return ok

    def _prefer_by_cuisine(self, recipes: List[Meal], cuisine: str) -> List[Meal]:
        """
        超轻量偏好：根据菜名关键词做倾向（不做硬过滤，避免可选为空）。
        """
        c = (cuisine or "").strip()
        if not c:
            return recipes

        # “清淡/微辣/川菜”等关键词
        mild_kw = ["清蒸", "清炖", "清炒", "白灼", "水煮", "清汤", "蒸", "凉拌"]
        spicy_kw = ["麻", "辣", "香辣", "麻辣", "红油", "水煮", "干锅", "川", "泡椒", "剁椒"]
        home_kw = ["家常", "红烧", "番茄", "土豆", "炒", "炖", "汤"]

        def score(name: str) -> int:
            n = name
            if "清淡" in c:
                return 2 if any(k in n for k in mild_kw) else 0
            if "川" in c or "辣" in c or "微辣" in c:
                return 2 if any(k in n for k in spicy_kw) else 0
            if "家常" in c:
                return 2 if any(k in n for k in home_kw) else 0
            return 0

        scored = [(score(r.name), r) for r in recipes]
        # 如果完全没分差，就原样
        if all(s == 0 for s, _ in scored):
            return recipes

        # 按分数把“更匹配的”放前面，后续抽样会偏向前部
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]

    def _choose_one(self, pool: List[Meal], used_names: set[str], soft_avoid: set[str] | None = None) -> Meal:
        """
        从 pool 里选一个不重复的。找不到就允许重复。
        soft_avoid：用于“避免连续重复”。
        """
        soft_avoid = soft_avoid or set()

        # 先尝试：不在 used_names 且不在 soft_avoid
        candidates = [m for m in pool if m.name not in used_names and m.name not in soft_avoid]
        if candidates:
            return self._rng.choice(candidates)

        # 再尝试：不在 used_names
        candidates = [m for m in pool if m.name not in used_names]
        if candidates:
            return self._rng.choice(candidates)

        # 最后：随便选
        return self._rng.choice(pool)

    def plan(self, prefs: UserPrefs, fridge_path: str = "data/fridge.json") -> Tuple[List[DayPlan], Dict[str, str]]:
        fridge = {}
        try:
            fridge = self.read_json.run(fridge_path)
        except Exception:
            fridge = {}

        recipes = self._filter_recipes(prefs.avoid)
        if not recipes:
            recipes = DEFAULT_RECIPE_DB

        recipes = self._prefer_by_cuisine(recipes, prefs.cuisine)

        # 早餐倾向：面/粥/蛋/汤/饼/包/煎等（仅用于排序倾向，不做硬过滤）
        breakfast_kw = ["面", "粥", "蛋", "汤", "饼", "包", "馒头", "煎", "蒸", "三明治", "吐司", "馄饨", "饺", "粉"]
        def breakfast_score(m: Meal) -> int:
            return 1 if any(k in m.name for k in breakfast_kw) else 0

        breakfast_pool = sorted(recipes, key=lambda m: breakfast_score(m), reverse=True)
        main_pool = recipes[:]  # 午晚餐池：全量

        day_plans: List[DayPlan] = []
        used_overall: set[str] = set()
        prev_day_names: set[str] = set()

        for i in range(prefs.days):
            used_today: set[str] = set()

            b = self._choose_one(breakfast_pool[: max(30, len(breakfast_pool))], used_today | used_overall, soft_avoid=prev_day_names)
            used_today.add(b.name)

            l = self._choose_one(main_pool[: max(60, len(main_pool))], used_today | used_overall, soft_avoid=prev_day_names)
            used_today.add(l.name)

            d = self._choose_one(main_pool[: max(60, len(main_pool))], used_today | used_overall, soft_avoid=prev_day_names)
            used_today.add(d.name)

            day_plans.append(DayPlan(day_index=i + 1, breakfast=b, lunch=l, dinner=d))

            used_overall |= used_today
            prev_day_names = used_today

        # 合并购物清单（MVP：不做精确数量累加）
        need: Dict[str, str] = {}
        try:
            have_all = sum((fridge.get(cat, []) for cat in fridge.keys()), [])
        except Exception:
            have_all = []

        for dp in day_plans:
            for meal in (dp.breakfast, dp.lunch, dp.dinner):
                for k, v in meal.ingredients.items():
                    if k in have_all:
                        continue
                    need[k] = "适量/按需"

        return day_plans, need

    def render_markdown(self, prefs: UserPrefs, plans: List[DayPlan]) -> str:
        lines = []
        lines.append(f"# {prefs.days} 天食谱规划（{prefs.people}人）")
        lines.append("")
        lines.append("## 偏好/约束")
        lines.append(f"- 人数：{prefs.people}")
        lines.append(f"- 天数：{prefs.days}")
        lines.append(f"- 菜系：{prefs.cuisine}")
        lines.append(f"- 忌口/过敏：{', '.join(prefs.avoid) if prefs.avoid else '无'}")
        lines.append("")
        for dp in plans:
            lines.append(f"## Day {dp.day_index}")
            for title, meal in [("早餐", dp.breakfast), ("午餐", dp.lunch), ("晚餐", dp.dinner)]:
                lines.append(f"### {title}：{meal.name}")
                lines.append("- 食材：")
                for ing, qty in meal.ingredients.items():
                    lines.append(f"  - {ing}：{qty}")
                lines.append("- 步骤：")
                for s in meal.steps:
                    lines.append(f"  1. {s}")
                lines.append("")
        return "\n".join(lines)

    def run(self, prefs: UserPrefs) -> None:
        plans, shopping = self.plan(prefs)
        md = self.render_markdown(prefs, plans)
        self.write_text.run("output/meal_plan.md", md)
        self.write_json.run("output/shopping_list.json", shopping)