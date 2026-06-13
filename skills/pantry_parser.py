# skills/pantry_parser.py
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from llm_qwen import get_qwen_client
from prompts import PANTRY_PARSE_SYSTEM


class PantryParseError(Exception):
    pass


def parse_pantry_input_with_llm(user_text: str, retries: int = 1) -> Dict:
    """
    使用大模型解析冰箱库存输入

    返回格式:
    {
        "action": "add" | "set" | "remove" | "clear",
        "items": [{"name": "鸡蛋", "quantity": 10, "unit": "个"}, ...]
    }
    """
    client = get_qwen_client()
    last_err: Exception | None = None

    for _ in range(retries + 1):
        try:
            raw = client.generate(
                prompt=f"用户输入：{user_text}",
                system=PANTRY_PARSE_SYSTEM,
                temperature=0.0,
            ).strip()

            # 清理可能的 markdown 代码块
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise PantryParseError(f"Model output is not a JSON object: {raw}")

            # 验证必需字段
            if "action" not in data:
                data["action"] = "add"
            if "items" not in data:
                data["items"] = []

            # 确保 items 是列表
            if not isinstance(data["items"], list):
                data["items"] = []

            # 标准化每个 item
            for item in data["items"]:
                if "unit" not in item:
                    item["unit"] = "个"
                if "quantity" not in item:
                    item["quantity"] = 1
                if "name" not in item:
                    continue

            return data

        except Exception as e:
            last_err = e

    raise PantryParseError(f"Failed to parse pantry input. Last error: {last_err}")


def parse_pantry_input_fallback(text: str) -> List[Dict]:
    """降级方案：正则解析（当大模型失败时使用）"""
    results = []

    patterns = [
        r'([\u4e00-\u9fa5]{2,4})(\d+(?:\.\d+)?)\s*([个个g斤公斤袋包盒把根棵]|克|千克)',
        r'([\u4e00-\u9fa5]{2,4})\s*(\d+)\s*个',
        r'([\u4e00-\u9fa5]{2,4})有(\d+)个',
        r'([\u4e00-\u9fa5]{2,4})还有(\d+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 3:
                name, qty, unit = match
            else:
                name, qty = match
                unit = "个"

            if unit in ["克"]:
                unit = "g"
            elif unit in ["千克", "公斤"]:
                unit = "kg"

            results.append({
                "name": name,
                "quantity": float(qty),
                "unit": unit
            })

    # 去重合并
    unique = {}
    for item in results:
        name = item["name"]
        if name in unique:
            unique[name]["quantity"] += item["quantity"]
        else:
            unique[name] = item

    return list(unique.values())