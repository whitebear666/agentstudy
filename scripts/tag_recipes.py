from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def infer_tags(name: str) -> Dict[str, Any]:
    """
    规则打标签（MVP 够用，后续可以扩充规则或改成模型打标）
    """
    n = name.strip()

    tags: Dict[str, Any] = {
        "meal_type": [],   # breakfast / lunch / dinner / snack
        "style": [],       # 清淡/家常/川湘/日式/韩式...
        "spicy": "unknown",# none / mild / medium / hot / unknown
        "method": [],      # 炒/炖/煮/蒸/烤/拌/炸/煎
        "is_soup": False
    }

    # ---- method ----
    method_map = {
        "炒": ["炒", "爆", "煸"],
        "炖": ["炖", "煲", "焖", "红烧", "卤"],
        "煮": ["煮", "汆", "涮"],
        "蒸": ["蒸"],
        "烤": ["烤", "焗"],
        "拌": ["拌", "凉拌"],
        "炸": ["炸"],
        "煎": ["煎"],
    }
    for m, kws in method_map.items():
        if any(k in n for k in kws):
            tags["method"].append(m)

    # ---- soup ----
    if "汤" in n or "羹" in n or "粥" in n:
        tags["is_soup"] = True
    if "汤" in n:
        tags["method"] = list(set(tags["method"] + ["煮"]))

    # ---- meal_type ----
    # 很粗但好用：带这些关键词的更像早餐/加餐
    breakfast_kw = ["粥", "面", "米粉", "馄饨", "包", "馒头", "饼", "吐司", "三明治", "蛋", "羹", "豆浆", "油条"]
    snack_kw = ["小吃", "甜", "糖水", "点心", "蛋糕", "饼干", "布丁"]
    if any(k in n for k in breakfast_kw):
        tags["meal_type"].append("breakfast")
    if any(k in n for k in snack_kw):
        tags["meal_type"].append("snack")
    # 默认都可做正餐
    tags["meal_type"] = list(set(tags["meal_type"] + ["lunch", "dinner"]))

    # ---- spicy ----
    # 以菜名关键词粗判断
    hot_kw = ["麻辣", "香辣", "变态辣", "重辣"]
    medium_kw = ["辣", "椒", "剁椒", "泡椒", "红油", "水煮", "干锅", "火锅"]
    mild_kw = ["微辣", "少辣"]
    none_kw = ["清汤", "清蒸", "白灼", "清炖", "清炒", "清淡"]

    if any(k in n for k in hot_kw):
        tags["spicy"] = "hot"
    elif any(k in n for k in mild_kw):
        tags["spicy"] = "mild"
    elif any(k in n for k in none_kw):
        tags["spicy"] = "none"
    elif any(k in n for k in medium_kw):
        tags["spicy"] = "medium"

    # ---- style ----
    if any(k in n for k in ["川", "麻婆", "回锅", "水煮", "干锅", "豆瓣"]):
        tags["style"].append("川湘")
    if any(k in n for k in ["日式", "照烧", "味噌"]):
        tags["style"].append("日式")
    if any(k in n for k in ["韩式", "泡菜", "辣酱"]):
        tags["style"].append("韩式")
    if any(k in n for k in ["清", "白灼"]):
        tags["style"].append("清淡")
    # 默认家常
    tags["style"] = list(set(tags["style"] + ["家常"]))

    # 去重
    tags["method"] = sorted(set(tags["method"]))
    tags["meal_type"] = sorted(set(tags["meal_type"]))
    tags["style"] = sorted(set(tags["style"]))

    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/recipes.json")
    ap.add_argument("--out", dest="out", default="data/recipes_tagged.json")
    args = ap.parse_args()

    in_path = Path(args.inp).resolve()
    out_path = Path(args.out).resolve()

    raw = load_json(in_path)
    if not isinstance(raw, list):
        raise SystemExit("recipes.json must be a list")

    tagged: List[Dict[str, Any]] = []
    for obj in raw:
        if not isinstance(obj, dict):
            continue
        name = obj.get("name")
        ingredients = obj.get("ingredients")
        steps = obj.get("steps")
        if not isinstance(name, str) or not isinstance(ingredients, dict) or not isinstance(steps, list):
            continue

        t = dict(obj)
        t["tags"] = infer_tags(name)
        tagged.append(t)

    save_json(out_path, tagged)
    print(f"[OK] tagged={len(tagged)} out={out_path}")


if __name__ == "__main__":
    main()