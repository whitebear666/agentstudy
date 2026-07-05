"""API layer regression tests.

Role:
    Verifies the FastAPI bridge used by the React frontend without requiring an
    HTTP test client dependency.

Related modules:
    api_server.py exposes structured generation and recipe shopping endpoints.
    agent.py writes the output artifacts read by the frontend.
"""

from __future__ import annotations

import os

import api_server


def _isolate_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api_server, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(api_server, "DATA_DIR", tmp_path / "data")
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)


def test_recipe_shopping_supports_exact_and_fuzzy_names():
    first = api_server.controller.agent.recipe_db[0]
    fuzzy = first.name[-2:]

    exact = api_server.recipe_shopping(api_server.RecipeShoppingRequest(names=[first.name]))
    fuzzy_result = api_server.recipe_shopping(api_server.RecipeShoppingRequest(names=[fuzzy]))

    assert exact["items"]
    assert fuzzy_result["items"]
    assert first.name in fuzzy_result["matched"]
    assert fuzzy_result["missing"] == []


def test_generate_endpoint_persists_dish_shape(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    response = api_server.generate(
        api_server.GenerateRequest(
            people=2,
            days=1,
            budget=120,
            cuisine="家常",
            avoid=[],
            dish_count=3,
            meat_count=1,
            vegetable_count=2,
            dinner_style="清淡",
        )
    )

    prefs = response["artifacts"]["prefs"]
    assert prefs["dish_count"] == 3
    assert prefs["meat_count"] == 1
    assert prefs["vegetable_count"] == 2
    assert "每餐菜数：3 道" in response["artifacts"]["mealPlanMarkdown"]
    assert response["artifacts"]["menu"]
    dinner = response["artifacts"]["menu"][0]["meals"]["dinner"]
    assert isinstance(dinner["timeline"], list)
    assert "parts" in dinner


def test_replace_endpoint_updates_structured_menu(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    api_server.generate(
        api_server.GenerateRequest(
            people=2,
            days=1,
            budget=120,
            cuisine="家常",
            avoid=[],
            dish_count=3,
            meat_count=1,
            vegetable_count=2,
        )
    )
    response = api_server.replace_menu_meal(
        api_server.ReplaceMealRequest(day=1, meal_type="dinner", part_type="main")
    )

    assert response["artifacts"]["menu"]
    assert response["artifacts"]["shoppingList"]
    assert "meal_plan.md" in response["reply"] or "output/meal_plan.md" in response["reply"]


def test_remove_endpoint_updates_menu_and_shopping(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    api_server.generate(
        api_server.GenerateRequest(
            people=2,
            days=1,
            budget=120,
            cuisine="家常",
            avoid=[],
            dish_count=3,
            meat_count=1,
            vegetable_count=2,
        )
    )
    response = api_server.remove_menu_meal(
        api_server.RemoveMealRequest(day=1, meal_type="dinner", part_type="side")
    )

    dinner = response["artifacts"]["menu"][0]["meals"]["dinner"]
    assert dinner["parts"]["side"] is None
    assert response["artifacts"]["shoppingList"] is not None
    assert "已删除" in response["reply"]


def test_generate_endpoint_excludes_blacklisted_recipe_name(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    blacklisted = api_server.controller.agent.recipe_db[0].name
    response = api_server.generate(
        api_server.GenerateRequest(
            people=2,
            days=1,
            budget=120,
            cuisine="家常",
            avoid=[],
            blacklist=[blacklisted],
            dish_count=3,
            meat_count=1,
            vegetable_count=2,
        )
    )

    names = []
    for day in response["artifacts"]["menu"]:
        for meal in day["meals"].values():
            for dish in meal["parts"].values():
                if dish:
                    names.append(dish["name"])

    assert blacklisted not in names
    assert blacklisted in response["artifacts"]["prefs"]["avoid"]


def test_generate_endpoint_prioritizes_favorite_recipe(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    favorite = api_server.controller.agent.recipe_db[0].name
    response = api_server.generate(
        api_server.GenerateRequest(
            people=2,
            days=1,
            budget=120,
            cuisine="家常",
            avoid=[],
            favorites=[favorite],
            dish_count=3,
            meat_count=1,
            vegetable_count=2,
        )
    )

    names = []
    for day in response["artifacts"]["menu"]:
        for meal in day["meals"].values():
            for dish in meal["parts"].values():
                if dish:
                    names.append(dish["name"])

    assert favorite in names
    assert favorite in response["artifacts"]["prefs"]["favorite_recipes"]
    matching = [
        dish
        for day in response["artifacts"]["menu"]
        for meal in day["meals"].values()
        for dish in meal["parts"].values()
        if dish and dish["name"] == favorite
    ]
    assert matching
    assert "你收藏过这道菜" in matching[0]["reasons"]


def test_pantry_endpoint_adds_and_deletes_items(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    added = api_server.pantry_add(
        api_server.PantryItemRequest(
            name="鸡蛋",
            quantity=6,
            unit="个",
            category="肉蛋奶",
            expiry_date="2026-07-08",
        )
    )
    assert any(item["name"] == "鸡蛋" and item["expiry_date"] == "2026-07-08" for item in added["items"])

    deleted = api_server.pantry_delete(api_server.PantryDeleteRequest(name="鸡蛋"))
    assert all(item["name"] != "鸡蛋" for item in deleted["items"])


def test_generate_deducts_pantry_items_from_shopping_list(tmp_path, monkeypatch):
    _isolate_outputs(tmp_path, monkeypatch)

    api_server.pantry_add(
        api_server.PantryItemRequest(name="鸡蛋", quantity=6, unit="个", category="肉蛋奶")
    )
    response = api_server.generate(
        api_server.GenerateRequest(
            people=2,
            days=1,
            budget=120,
            cuisine="家常",
            avoid=[],
            favorites=["西红柿炒蛋"],
            dish_count=3,
            meat_count=1,
            vegetable_count=2,
        )
    )

    shopping = response["artifacts"]["shoppingList"]["items"]
    assert "鸡蛋" not in shopping
