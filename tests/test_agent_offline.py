# tests/test_agent_offline.py
#这里是离线测试
from __future__ import annotations

import json
import os

from agent import GroceryMealAgent
from models import UserPrefs


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