# agent.py
from __future__ import annotations
from typing import Dict, List, Tuple
from models import UserPrefs, Meal, DayPlan
from tools import ReadJsonTool, WriteJsonTool, WriteTextTool

RECIPE_DB = [
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
    def __init__(self):
        self.read_json = ReadJsonTool()
        self.write_json = WriteJsonTool()
        self.write_text = WriteTextTool()

    def _filter_recipes(self, avoid: List[str] | None) -> List[Meal]:
        if not avoid:
            return RECIPE_DB
        avoid_set = set(avoid)
        ok = []
        for r in RECIPE_DB:
            if any(item in avoid_set for item in r.ingredients.keys()):
                continue
            ok.append(r)
        return ok

    def plan(self, prefs: UserPrefs, fridge_path: str = "data/fridge.json") -> Tuple[List[DayPlan], Dict[str, str]]:
        fridge = {}
        try:
            fridge = self.read_json.run(fridge_path)
        except Exception:
            fridge = {}

        recipes = self._filter_recipes(prefs.avoid)

        # 简单轮换：早餐=拌面/炒饭轮换，午晚=炒蛋/炖鸡轮换
        breakfast_candidates = [r for r in recipes if r.name in ("葱油拌面", "蛋炒饭")]
        main_candidates = [r for r in recipes if r.name in ("西红柿炒蛋", "土豆炖鸡胸")]

        if not breakfast_candidates:
            breakfast_candidates = recipes[:]
        if not main_candidates:
            main_candidates = recipes[:]

        day_plans: List[DayPlan] = []
        for i in range(prefs.days):
            b = breakfast_candidates[i % len(breakfast_candidates)]
            l = main_candidates[i % len(main_candidates)]
            d = main_candidates[(i + 1) % len(main_candidates)]
            day_plans.append(DayPlan(day_index=i + 1, breakfast=b, lunch=l, dinner=d))

        # 合并购物清单（这里只做简单文本汇总）
        need: Dict[str, str] = {}
        for dp in day_plans:
            for meal in (dp.breakfast, dp.lunch, dp.dinner):
                for k, v in meal.ingredients.items():
                    # 如果冰箱里有则不买（演示版：只要出现过就认为有）
                    have_all = sum((fridge.get(cat, []) for cat in fridge.keys()), [])
                    if k in have_all:
                        continue
                    need[k] = "适量/按需"  # MVP：不做精确数量累加

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