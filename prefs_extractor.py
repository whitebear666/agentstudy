# prefs_extractor.py
from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from llm_qwen import get_qwen_client, QwenAPIError
from models import UserPrefs
from prompts import PREFS_EXTRACT_SYSTEM, PREFS_UPDATE_SYSTEM



class PrefsExtractError(Exception):
    pass


def _clamp_int(v: Any, default: int, lo: int, hi: int) -> int:
    try:
        iv = int(v)
    except Exception:
        return default
    return max(lo, min(hi, iv))


def _as_float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _as_str_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, str) and x.strip():
                out.append(x.strip())
        return out
    # 如果模型输出成了字符串，做一次兼容
    if isinstance(v, str):
        return [s for s in v.replace("，", " ").split() if s.strip()]
    return []


def extract_prefs_with_qwen(user_text: str, retries: int = 1) -> UserPrefs:
    client = get_qwen_client()

    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            raw = client.generate(
                prompt=f"用户输入：{user_text}",
                system=PREFS_EXTRACT_SYSTEM,
                temperature=0.0,
            )

            # 兼容：有时模型会在 JSON 前后加空白
            raw = raw.strip()

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise PrefsExtractError(f"Model output is not a JSON object: {raw}")

            people = _clamp_int(data.get("people", 2), default=2, lo=1, hi=10)
            days = _clamp_int(data.get("days", 3), default=3, lo=1, hi=14)
            budget = _as_float_or_none(data.get("budget", None))
            avoid = _as_str_list(data.get("avoid", []))
            cuisine = data.get("cuisine", "家常")
            if not isinstance(cuisine, str) or not cuisine.strip():
                cuisine = "家常"

            return UserPrefs(
                people=people,
                days=days,
                budget=budget,
                avoid=avoid if avoid else None,
                cuisine=cuisine.strip(),
                has_kitchen=True,
            )
        except Exception as e:
            last_err = e

    raise PrefsExtractError(f"Failed to extract prefs. Last error: {last_err}")

def extract_prefs_update_with_qwen(user_text: str, retries: int = 1) -> Dict[str, Any]:
    """
    增量抽取：只返回本轮提到/要修改的字段。未提到字段为 None。
    返回示例：
      {"people": None, "days": 5, "budget": None, "avoid": None, "cuisine": None}
    """
    local = extract_prefs_update_local(user_text)
    if any(local.get(k) is not None for k in ["people", "days", "avoid", "cuisine"]) or ("budget" in local):
        # budget 这里你可以更严格一点：如果 text 里出现“不限/预算xxx”，就直接返回 local
        # 为简单起见：只要 local 抽到任何东西就直接用
        if any(v is not None for v in local.values()) or local.get("avoid") == []:
            return local
    client = get_qwen_client()

    last_err: Exception | None = None

    def _clean_partial(data: Dict[str, Any]) -> Dict[str, Any]:
        people = data.get("people", None)
        days = data.get("days", None)
        budget = data.get("budget", None)
        avoid = data.get("avoid", None)
        cuisine = data.get("cuisine", None)

        # people/days：允许 None，不允许乱值
        people = None if people is None else _clamp_int(people, default=2, lo=1, hi=10)
        days = None if days is None else _clamp_int(days, default=3, lo=1, hi=14)

        # budget：允许 None；非 None 转 float
        budget = _as_float_or_none(budget)

        # avoid：允许 None（表示没提）；[] 表示明确“无忌口”
        if avoid is None:
            pass
        else:
            avoid = _as_str_list(avoid)

        # cuisine：允许 None；非空字符串才保留
        if cuisine is None:
            pass
        elif not isinstance(cuisine, str) or not cuisine.strip():
            cuisine = None
        else:
            cuisine = cuisine.strip()

        return {
            "people": people,
            "days": days,
            "budget": budget,   # 允许 None 覆盖（表示用户说不限）
            "avoid": avoid,     # None=没提；[]/["香菜"]=明确更新
            "cuisine": cuisine,
        }

    # 先尝试 structured output（如果 DashScope 不支持会抛错，自动回退）
    for attempt in range(retries + 1):
        try:
            raw = client.generate(
                prompt=f"用户输入：{user_text}",
                system=PREFS_UPDATE_SYSTEM,
                temperature=0.0,
            ).strip()

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise PrefsExtractError(f"Model output is not a JSON object: {raw}")
            return _clean_partial(data)
        except Exception as e:
            last_err = e

    # 回退：不带 response_format 再试一次（有些接口不支持 structured output）
    for attempt in range(retries + 1):
        try:
            raw = client.generate(
                prompt=f"用户输入：{user_text}",
                system=PREFS_UPDATE_SYSTEM,
                temperature=0.0,
            ).strip()

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise PrefsExtractError(f"Model output is not a JSON object: {raw}")
            return _clean_partial(data)
        except Exception as e:
            last_err = e

    raise PrefsExtractError(f"Failed to extract prefs update. Last error: {last_err}")

_CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
}

def _cn_to_int(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    # 仅支持 1-10 的常见中文（足够 MVP）
    if s in _CN_NUM:
        return _CN_NUM[s]
    return None

def extract_prefs_update_local(user_text: str) -> Dict[str, Any]:
    """
    尽力而为的本地兜底抽取（不调用大模型）。
    返回 partial dict；如果什么都没抽到，就返回全 None（caller 可决定是否继续走 Qwen）。
    """
    t = user_text.strip()

    partial: Dict[str, Any] = {
        "people": None,
        "days": None,
        "budget": None,   # 注意：这里 None 表示“没抽到”；如果抽到“不限”我们用键来表示确认（见下）
        "avoid": None,
        "cuisine": None,
    }
    hit_any = False

    # people: "2人" "两个人"
    m = re.search(r"([0-9]+|[零一二两三四五六七八九十])\s*个?\s*人", t)
    if m:
        v = _cn_to_int(m.group(1))
        if v is not None:
            partial["people"] = v
            hit_any = True

    # days: "3天" "三天"
    m = re.search(r"([0-9]+|[零一二两三四五六七八九十])\s*天", t)
    if m:
        v = _cn_to_int(m.group(1))
        if v is not None:
            partial["days"] = v
            hit_any = True

    # budget: "预算150" "150元" "不限预算"
    if any(k in t for k in ["不限", "无预算", "不限制预算"]):
        # 表示用户明确说了不限：用 budget 键出现来确认
        partial["budget"] = None
        hit_any = True
    else:
        m = re.search(r"(预算\s*)?([0-9]+(\.[0-9]+)?)\s*(元|块)?", t)
        if m and ("预算" in (m.group(1) or "") or "元" in (m.group(4) or "") or "块" in (m.group(4) or "")):
            partial["budget"] = float(m.group(2))
            hit_any = True

    # avoid: "不要香菜" / "别放香菜" / "忌口:辣椒" / "无忌口"
    if any(k in t for k in ["无忌口", "不忌口"]):
        partial["avoid"] = []
        hit_any = True
    else:
        # 简单抽取：匹配 “不要X”“别放X”“忌口X”
        avoids = []
        for pat in [r"(不要|别放|别吃)\s*([^\s，。,\.]+)", r"忌口[:：]?\s*([^\s，。,\.]+)"]:
            for m in re.finditer(pat, t):
                item = m.group(2 if m.lastindex and m.lastindex >= 2 else 1)
                if item:
                    avoids.append(item.strip())
        if avoids:
            partial["avoid"] = list(dict.fromkeys(avoids))
            hit_any = True

    # cuisine: very rough keywords
    if "清淡" in t:
        partial["cuisine"] = "清淡"
        hit_any = True
    elif "家常" in t:
        partial["cuisine"] = "家常"
        hit_any = True
    elif "川菜" in t:
        partial["cuisine"] = "川菜"
        hit_any = True

    if not hit_any:
        # 什么都没抽到：返回全 None，caller 决定是否走 Qwen
        return {
            "people": None,
            "days": None,
            "budget": None,
            "avoid": None,
            "cuisine": None,
        }

    # 这里的 partial 仍然需要复用你现有的 clean/clamp（如果有），但已足够兜底
    return partial