# skills/price_fetcher.py
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass, asdict


@dataclass
class PriceInfo:
    """价格信息"""
    price: float
    unit: str
    source: str
    updated_at: str
    store: str = "参考价"


class PriceFetcher:
    """
    价格获取器 - 模拟数据版
    使用本地价格数据库，稳定可靠
    后续可升级为真实爬虫
    """

    CACHE_FILE = "data/price_cache.json"
    CACHE_EXPIRE_HOURS = 168  # 7天

    # 模拟价格数据（元/单位）
    MOCK_PRICES = {
        # 蔬菜类
        "白菜": (2.5, "斤"), "菠菜": (5.0, "斤"), "生菜": (4.0, "斤"), "油菜": (3.5, "斤"),
        "芹菜": (4.0, "斤"), "韭菜": (5.0, "斤"), "西兰花": (7.0, "斤"), "菜花": (5.0, "斤"),
        "西红柿": (5.0, "斤"), "番茄": (5.0, "斤"), "黄瓜": (4.0, "斤"), "冬瓜": (3.0, "斤"),
        "南瓜": (3.5, "斤"), "苦瓜": (6.0, "斤"), "茄子": (4.5, "斤"), "土豆": (3.0, "斤"),
        "胡萝卜": (3.5, "斤"), "白萝卜": (2.5, "斤"), "洋葱": (3.0, "斤"), "豆角": (6.0, "斤"),
        "青椒": (6.0, "斤"), "辣椒": (8.0, "斤"), "蘑菇": (10.0, "斤"), "香菇": (12.0, "斤"),
        "金针菇": (8.0, "斤"), "木耳": (8.0, "斤"), "玉米": (4.0, "根"),

        # 肉蛋类
        "猪肉": (28.0, "斤"), "牛肉": (55.0, "斤"), "羊肉": (60.0, "斤"), "鸡肉": (18.0, "斤"),
        "鸡胸": (22.0, "斤"), "鸭肉": (16.0, "斤"), "排骨": (35.0, "斤"), "五花肉": (30.0, "斤"),
        "鸡蛋": (1.0, "个"), "鸭蛋": (1.5, "个"),

        # 水产品
        "鱼": (15.0, "斤"), "鲤鱼": (12.0, "斤"), "草鱼": (12.0, "斤"), "鲫鱼": (15.0, "斤"),
        "虾": (38.0, "斤"), "对虾": (38.0, "斤"),

        # 主食类
        "大米": (5.0, "斤"), "面粉": (4.0, "斤"), "面条": (5.0, "斤"), "米粉": (6.0, "斤"),
        "面包": (12.0, "袋"), "馒头": (1.0, "个"),

        # 调料类
        "盐": (3.0, "袋"), "糖": (5.0, "袋"), "酱油": (10.0, "瓶"), "生抽": (12.0, "瓶"),
        "老抽": (12.0, "瓶"), "醋": (8.0, "瓶"), "料酒": (10.0, "瓶"), "蚝油": (15.0, "瓶"),
        "香油": (18.0, "瓶"), "豆瓣酱": (15.0, "瓶"), "姜": (6.0, "块"), "蒜": (8.0, "头"),
        "葱": (2.0, "把"), "香菜": (3.0, "把"),
    }

    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """加载价格缓存"""
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                expire_time = datetime.now() - timedelta(hours=self.CACHE_EXPIRE_HOURS)
                return {k: v for k, v in data.items()
                        if datetime.fromisoformat(v['updated_at']) > expire_time}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self) -> None:
        """保存价格缓存"""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")

    def _get_mock_price(self, name: str) -> Tuple[float, str]:
        """获取模拟价格"""
        # 精确匹配
        if name in self.MOCK_PRICES:
            return self.MOCK_PRICES[name]

        # 模糊匹配
        for key, (price, unit) in self.MOCK_PRICES.items():
            if key in name or name in key:
                return (price, unit)

        # 默认价格
        return (5.0, "份")

    def get_price(self, name: str, force_refresh: bool = False, user_callback=None) -> PriceInfo:
        """
        获取食材价格
        优先级：缓存 → 模拟数据
        """
        name = name.strip()

        # 1. 检查缓存
        if not force_refresh and name in self.cache:
            data = self.cache[name]
            return PriceInfo(**data)

        # 2. 获取模拟价格
        price, unit = self._get_mock_price(name)

        # 添加小幅随机波动，更真实
        price = round(price * random.uniform(0.95, 1.05), 1)

        price_info = PriceInfo(
            price=price,
            unit=unit,
            source="mock",
            updated_at=datetime.now().isoformat(),
            store="模拟价格"
        )

        # 保存到缓存
        self.cache[name] = asdict(price_info)
        self._save_cache()

        return price_info

    def get_prices_batch(self, names: List[str], force_refresh: bool = False, user_callback=None) -> Dict[
        str, PriceInfo]:
        """批量获取价格"""
        results = {}
        for name in names:
            results[name] = self.get_price(name, force_refresh, user_callback)
        return results


def create_price_input_dialog(root, name):
    """创建价格输入对话框"""
    return None