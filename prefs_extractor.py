# prefs_extractor.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from llm_qwen import get_qwen_client, QwenAPIError
from models import UserPrefs
from prompts import PREFS_EXTRACT_SYSTEM


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