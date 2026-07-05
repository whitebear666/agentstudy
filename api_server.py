"""FastAPI backend for the web UI.

Role:
    Exposes the existing meal-planning controller through HTTP endpoints so the
    React/Vite frontend can chat with the agent and read generated artifacts.

Related modules:
    agent_controller.py owns chat, preference, pantry, and generation behavior.
    agent.py writes meal_plan.md and shopping-list artifacts.
    frontend/ contains the React client that calls these endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_controller import AgentController
from skills.cooking_profile import build_mealset_timeline


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

app = FastAPI(title="Meal Planning Agent API")
controller = AgentController()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class GenerateRequest(BaseModel):
    people: int = 2
    days: int = 1
    budget: Optional[float] = None
    cuisine: str = "家常"
    avoid: List[str] = []
    blacklist: List[str] = []
    favorites: List[str] = []
    dish_count: Optional[int] = None
    meat_count: Optional[int] = None
    vegetable_count: Optional[int] = None
    breakfast_style: Optional[str] = None
    lunch_style: Optional[str] = None
    dinner_style: Optional[str] = None
    health_goal: Optional[str] = None


class RecipeShoppingRequest(BaseModel):
    names: List[str]


class ReplaceMealRequest(BaseModel):
    day: int = 1
    meal_type: str = "dinner"
    part_type: str = "main"
    constraint: Optional[str] = None


class RemoveMealRequest(BaseModel):
    day: int = 1
    meal_type: str = "dinner"
    part_type: str = "main"


class PantryItemRequest(BaseModel):
    name: str
    quantity: float = 1
    unit: str = "份"
    category: str = "其他"
    expiry_date: Optional[str] = None


class PantryDeleteRequest(BaseModel):
    name: str


def _read_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pantry_items() -> List[Dict[str, Any]]:
    pantry = _read_json(DATA_DIR / "pantry.json") or {}
    if not isinstance(pantry, dict):
        return []
    items: List[Dict[str, Any]] = []
    for name, raw in pantry.items():
        if isinstance(raw, dict):
            items.append(
                {
                    "name": raw.get("name", name),
                    "quantity": raw.get("quantity", 1),
                    "unit": raw.get("unit", "份"),
                    "category": raw.get("category", "其他"),
                    "expiry_date": raw.get("expiry_date"),
                }
            )
        else:
            items.append({"name": name, "quantity": 1, "unit": "份", "category": "其他"})
    return items


def _artifacts() -> Dict[str, Any]:
    return {
        "mealPlanMarkdown": _read_text(OUTPUT_DIR / "meal_plan.md"),
        "shoppingList": _read_json(OUTPUT_DIR / "shopping_list.json"),
        "optimizedShoppingList": _read_json(OUTPUT_DIR / "shopping_list_optimized.json"),
        "nutritionReportMarkdown": _read_text(OUTPUT_DIR / "nutrition_report.md"),
        "prefs": _read_json(OUTPUT_DIR / "prefs.json"),
        "menu": _menu_payload(),
        "pantry": _pantry_items(),
    }


def _meal_payload(meal) -> Optional[Dict[str, Any]]:
    if not meal:
        return None
    return {
        "name": meal.name,
        "ingredients": meal.ingredients,
        "steps": meal.steps,
        "meta": {
            "difficulty": meal.meta.difficulty,
            "cook_time_minutes": meal.meta.cook_time_minutes,
            "score": meal.meta.score,
            "time_source": meal.meta.time_source,
        },
        "reasons": _recipe_reasons(meal),
    }


def _mealset_payload(title: str, mealset) -> Dict[str, Any]:
    # Frontend MenuEditor expects each meal to carry its dishes and timeline together.
    return {
        "title": title,
        "parts": {
            "main": _meal_payload(mealset.main),
            "side": _meal_payload(mealset.side),
            "staple": _meal_payload(mealset.staple),
            "soup": _meal_payload(mealset.soup),
        },
        "timeline": _timeline_payload(mealset),
    }


def _menu_payload() -> List[Dict[str, Any]]:
    menu: List[Dict[str, Any]] = []
    for day in controller.current_day_plans:
        menu.append(
            {
                "day": day.day_index,
                "meals": {
                    "breakfast": _mealset_payload("早餐", day.breakfast),
                    "lunch": _mealset_payload("午餐", day.lunch),
                    "dinner": _mealset_payload("晚餐", day.dinner),
                },
            }
        )
    return menu


def _timeline_payload(mealset) -> List[Dict[str, Any]]:
    return [
        {"offset_minutes": item.offset_minutes, "title": item.title}
        for item in build_mealset_timeline(mealset)
    ]


def _recipe_reasons(meal) -> List[str]:
    if not meal:
        return []
    prefs = controller.state.prefs
    pantry_names = {item["name"] for item in _pantry_items()}
    reasons: List[str] = []
    if prefs.favorite_recipes and meal.name in prefs.favorite_recipes:
        reasons.append("你收藏过这道菜")
    matched_stock = [name for name in meal.ingredients if any(stock == name or stock in name or name in stock for stock in pantry_names)]
    if matched_stock:
        reasons.append("用到了库存：" + "、".join(matched_stock[:3]))
    if meal.meta.cook_time_minutes and meal.meta.cook_time_minutes <= 30:
        reasons.append("30 分钟内可完成")
    if meal.meta.difficulty and meal.meta.difficulty <= 2:
        reasons.append("难度较低")
    if prefs.health_goal:
        reasons.append(f"匹配健康目标：{prefs.health_goal}")
    return reasons[:4]


def _recipe_payload() -> List[Dict[str, Any]]:
    recipes: List[Dict[str, Any]] = []
    for meal in controller.agent.recipe_db:
        tags = controller.agent.recipe_meta.get(meal.name, {})
        recipes.append(
            {
                "name": meal.name,
                "ingredients": meal.ingredients,
                "steps": meal.steps,
                "meta": {
                    "difficulty": meal.meta.difficulty,
                    "cook_time_minutes": meal.meta.cook_time_minutes,
                    "score": meal.meta.score,
                    "time_source": meal.meta.time_source,
                },
                "tags": tags,
            }
        )
    return recipes


def _shopping_for_recipe_names(names: List[str]) -> Dict[str, str]:
    wanted = {name.strip() for name in names if name.strip()}
    shopping: Dict[str, str] = {}
    for meal in controller.agent.recipe_db:
        meal_name = meal.name.strip()
        is_match = any(want == meal_name or want in meal_name or meal_name in want for want in wanted)
        if not is_match:
            continue
        for name, qty in meal.ingredients.items():
            shopping[name] = qty
    return shopping


def _matched_recipe_names(names: List[str]) -> List[str]:
    wanted = [name.strip() for name in names if name.strip()]
    matched: List[str] = []
    for meal in controller.agent.recipe_db:
        meal_name = meal.name.strip()
        if any(want == meal_name or want in meal_name or meal_name in want for want in wanted):
            matched.append(meal_name)
    return matched


def _find_mealset(day: int, meal_type: str):
    for plan in controller.current_day_plans:
        if plan.day_index != day:
            continue
        if meal_type == "breakfast":
            return plan.breakfast
        if meal_type == "lunch":
            return plan.lunch
        if meal_type == "dinner":
            return plan.dinner
    return None


def _persist_current_menu() -> None:
    if not controller.current_prefs:
        return
    md = controller.agent.render_markdown(controller.current_prefs, controller.current_day_plans)
    controller.agent.write_text.run("output/meal_plan.md", md)
    controller.agent.write_json.run("output/shopping_list.json", controller.current_shopping)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/api/state")
def state() -> Dict[str, Any]:
    return {"artifacts": _artifacts(), "recipes": _recipe_payload()}


@app.post("/api/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    reply = controller.handle_user_message(req.message)
    return {
        "reply": reply,
        "artifacts": _artifacts(),
    }


@app.post("/api/generate")
def generate(req: GenerateRequest) -> Dict[str, Any]:
    prefs = controller.state.prefs
    prefs.people = max(1, min(10, int(req.people)))
    prefs.days = max(1, min(14, int(req.days)))
    prefs.budget = req.budget
    prefs.cuisine = (req.cuisine or "家常").strip()
    avoid_items = [item.strip() for item in [*req.avoid, *req.blacklist] if item.strip()]
    prefs.avoid = list(dict.fromkeys(avoid_items)) or None
    prefs.dish_count = req.dish_count
    prefs.meat_count = req.meat_count
    prefs.vegetable_count = req.vegetable_count
    prefs.breakfast_style = req.breakfast_style
    prefs.lunch_style = req.lunch_style
    prefs.dinner_style = req.dinner_style
    prefs.health_goal = req.health_goal
    prefs.favorite_recipes = [item.strip() for item in req.favorites if item.strip()] or None
    controller.state.confirmed_fields.update({"people", "days"})
    reply = controller.generate()
    return {"reply": reply, "artifacts": _artifacts(), "recipes": _recipe_payload()}


@app.get("/api/recipes")
def recipes() -> Dict[str, Any]:
    return {"recipes": _recipe_payload()}


@app.post("/api/recipes/shopping")
def recipe_shopping(req: RecipeShoppingRequest) -> Dict[str, Any]:
    matched = _matched_recipe_names(req.names)
    missing = [
        name
        for name in req.names
        if not any(name.strip() == item or name.strip() in item or item in name.strip() for item in matched)
    ]
    return {
        "items": _shopping_for_recipe_names(req.names),
        "matched": matched,
        "missing": missing,
    }


@app.post("/api/menu/replace")
def replace_menu_meal(req: ReplaceMealRequest) -> Dict[str, Any]:
    reply = controller.replace_meal(
        day=req.day,
        meal_type=req.meal_type,
        part_type=req.part_type,
        constraint=req.constraint,
    )
    return {"reply": reply, "artifacts": _artifacts(), "recipes": _recipe_payload()}


@app.post("/api/menu/remove")
def remove_menu_meal(req: RemoveMealRequest) -> Dict[str, Any]:
    mealset = _find_mealset(req.day, req.meal_type)
    if mealset is None or req.part_type not in {"main", "side", "staple", "soup"}:
        return {"reply": "未找到要删除的菜。", "artifacts": _artifacts(), "recipes": _recipe_payload()}
    old_meal = getattr(mealset, req.part_type, None)
    if old_meal is None:
        return {"reply": "这个位置本来就是空的。", "artifacts": _artifacts(), "recipes": _recipe_payload()}

    setattr(mealset, req.part_type, None)
    controller._rebuild_shopping_list()
    _persist_current_menu()
    return {
        "reply": f"已删除 {old_meal.name}，并更新购物清单。",
        "artifacts": _artifacts(),
        "recipes": _recipe_payload(),
    }


@app.get("/api/pantry")
def pantry_state() -> Dict[str, Any]:
    return {"items": _pantry_items()}


@app.post("/api/pantry")
def pantry_add(req: PantryItemRequest) -> Dict[str, Any]:
    pantry = _read_json(DATA_DIR / "pantry.json") or {}
    if not isinstance(pantry, dict):
        pantry = {}
    name = req.name.strip()
    if not name:
        return {"items": _pantry_items(), "artifacts": _artifacts()}
    pantry[name] = {
        "name": name,
        "quantity": req.quantity,
        "unit": req.unit.strip() or "份",
        "category": req.category.strip() or "其他",
        "expiry_date": req.expiry_date,
    }
    _write_json(DATA_DIR / "pantry.json", pantry)
    return {"items": _pantry_items(), "artifacts": _artifacts()}


@app.post("/api/pantry/delete")
def pantry_delete(req: PantryDeleteRequest) -> Dict[str, Any]:
    pantry = _read_json(DATA_DIR / "pantry.json") or {}
    if isinstance(pantry, dict):
        pantry.pop(req.name.strip(), None)
        _write_json(DATA_DIR / "pantry.json", pantry)
    return {"items": _pantry_items(), "artifacts": _artifacts()}
