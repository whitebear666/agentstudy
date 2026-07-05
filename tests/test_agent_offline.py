"""离线回归测试模块。

作用：
    验证核心生成链路不依赖 Qwen API 也能创建输出文件，并覆盖烹饪
    时间/难度抽取逻辑。

关联模块：
    agent.py 是主要被测对象。
    skills/cooking_profile.py 提供时间和难度抽取能力。
"""

# tests/test_agent_offline.py
#这里是离线测试
from __future__ import annotations

import json
import os

from agent import GroceryMealAgent
from models import Meal, MealSet, UserPrefs
from prefs_extractor import extract_prefs_update_local
from skills.cooking_profile import build_mealset_timeline, build_recipe_meta, mealset_total_time
from skills.recipe_quality import clean_recipe_object


def test_agent_run_creates_outputs(tmp_path, monkeypatch):
    # 切到临时目录，避免污染你的 output/
    monkeypatch.chdir(tmp_path)

    # 确保 data/fridge.json 可读：把仓库 data 目录映射过来
    # 这里假设你 agent.py 里是读取相对路径 data/fridge.json（如果不是，你告诉我我再改）
    os.makedirs("data", exist_ok=True)
    with open("data/fridge.json", "w", encoding="utf-8") as f:
        json.dump({"items": ["鸡蛋", "米"]}, f, ensure_ascii=False)

    os.makedirs("output", exist_ok=True)

    prefs = UserPrefs(
        people=2,
        days=3,
        budget=150,
        avoid=["香菜"],
        cuisine="家常",
        has_kitchen=True,
    )

    agent = GroceryMealAgent()
    agent.run(prefs)

    assert os.path.exists("output/meal_plan.md")
    assert os.path.exists("output/shopping_list.json")

    with open("output/shopping_list.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], dict)
    assert "categories" in data
    assert isinstance(data["categories"], dict)


def test_cooking_profile_extracts_time_and_difficulty():
    meta = build_recipe_meta(
        "清蒸鲈鱼",
        [
            "清蒸鲈鱼做法简单，从备料到出锅大约需要 30 分钟。",
            "预估烹饪难度：★★★",
        ],
        {"method": ["蒸"]},
    )

    assert meta.difficulty == 3
    assert meta.cook_time_minutes == 30
    assert meta.time_source == "parsed"
    assert meta.score is not None


def test_cooking_profile_prefers_total_time_over_step_timer():
    meta = build_recipe_meta(
        "红烧鱼",
        [
            "从备料到出锅，大约需要 40 分钟。",
            "3-4 分钟后翻面。",
            "预估烹饪难度：★★★★",
        ],
        {"method": ["炖"]},
    )

    assert meta.difficulty == 4
    assert meta.cook_time_minutes == 40


def test_local_prefs_extracts_dish_shape():
    partial = extract_prefs_update_local("2个人，每餐3道菜，一荤两素，预算150")

    assert partial["people"] == 2
    assert partial["dish_count"] == 3
    assert partial["meat_count"] == 1
    assert partial["vegetable_count"] == 2
    assert partial["budget"] == 150


def test_timeline_overlaps_waiting_time():
    stew = Meal(
        name="土豆炖鸡",
        ingredients={"鸡肉": "300g"},
        steps=["炖煮到软烂，大约需要45分钟"],
        meta=build_recipe_meta("土豆炖鸡", ["炖煮到软烂，大约需要45分钟"], {"method": ["炖"]}),
    )
    stir = Meal(
        name="清炒青菜",
        ingredients={"青菜": "300g"},
        steps=["洗菜切菜后快炒，大约需要15分钟"],
        meta=build_recipe_meta("清炒青菜", ["洗菜切菜后快炒，大约需要15分钟"], {"method": ["炒"]}),
    )
    mealset = MealSet(main=stew, side=stir)

    assert mealset_total_time(mealset) < 60
    titles = [item.title for item in build_mealset_timeline(mealset)]
    assert any("等待时间" in title or "洗切" in title for title in titles)


def test_recipe_quality_cleans_noise_and_enriches_tags():
    cleaned = clean_recipe_object(
        {
            "name": "  1. 清蒸鲈鱼  ",
            "ingredients": {"鲈鱼": "1条", "步骤": "不要", "葱": "少许"},
            "steps": [
                "1. 鲈鱼处理干净，放葱姜。",
                "![image](http://example.com/a.jpg)",
                "预计卡路里：300",
                "上锅清蒸 12 分钟。",
            ],
        }
    )

    assert cleaned is not None
    assert cleaned["name"] == "清蒸鲈鱼"
    assert "步骤" not in cleaned["ingredients"]
    assert cleaned["steps"] == ["鲈鱼处理干净，放葱姜。", "上锅清蒸 12 分钟。"]
    assert "蒸" in cleaned["tags"]["method"]
    assert "清淡" in cleaned["tags"]["style"]


def test_agent_prefers_expiring_pantry_ingredients(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    with open("data/recipes_tagged.json", "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "name": "牛肉小炒",
                    "ingredients": {"牛肉": "200g", "青椒": "1个"},
                    "steps": ["牛肉切片，青椒切块。", "热锅快炒 10 分钟。"],
                    "tags": {"meal_type": ["lunch", "dinner"], "method": ["炒"], "style": ["家常"]},
                },
                {
                    "name": "鸡蛋炒虾仁",
                    "ingredients": {"鸡蛋": "2个", "虾仁": "150g"},
                    "steps": ["鸡蛋打散，虾仁处理干净。", "下锅炒熟。"],
                    "tags": {"meal_type": ["lunch", "dinner"], "method": ["炒"], "style": ["家常"]},
                },
            ],
            f,
            ensure_ascii=False,
        )
    with open("data/pantry.json", "w", encoding="utf-8") as f:
        json.dump({"鸡蛋": {"name": "鸡蛋", "quantity": 2, "unit": "个", "expiry_date": "2026-07-06"}}, f, ensure_ascii=False)

    agent = GroceryMealAgent()
    plans, _ = agent.plan(UserPrefs(people=2, days=1, cuisine="家常", dish_count=1, meat_count=1, vegetable_count=0))
    names = [
        meal.name
        for mealset in (plans[0].breakfast, plans[0].lunch, plans[0].dinner)
        for meal in (mealset.main, mealset.side, mealset.staple, mealset.soup)
        if meal
    ]

    assert "鸡蛋炒虾仁" in names
