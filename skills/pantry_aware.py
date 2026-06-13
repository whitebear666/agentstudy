# skills/pantry_aware.py
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from skills.pantry_parser import parse_pantry_input_with_llm, parse_pantry_input_fallback, PantryParseError


@dataclass
class PantryItem:
    """冰箱/库存中的单个食材"""
    name: str  # 食材名称
    quantity: float  # 数量
    unit: str  # 单位（个/g/斤/袋等）
    expiry_date: Optional[str] = None  # 过期日期 YYYY-MM-DD
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    category: str = "其他"  # 蔬菜/肉蛋奶/主食/调料/水果


class PantryAwareSkill:
    """
    冰箱/库存感知技能：
    - 管理用户家中的食材库存
    - 生成菜单时优先使用库存食材
    - 自动计算还需要买什么
    """

    STORAGE_FILE = "data/pantry.json"

    # 食材分类映射
    CATEGORY_MAP = {
        "蔬菜": ["白菜", "菠菜", "生菜", "油菜", "芹菜", "韭菜", "西兰花", "菜花",
                 "西红柿", "番茄", "黄瓜", "冬瓜", "南瓜", "苦瓜", "丝瓜", "茄子",
                 "土豆", "马铃薯", "红薯", "山药", "萝卜", "胡萝卜", "莲藕", "洋葱",
                 "蒜苗", "豆角", "四季豆", "豌豆", "蚕豆", "玉米", "青椒", "彩椒",
                 "辣椒", "蘑菇", "香菇", "金针菇", "木耳", "银耳", "海带", "紫菜"],

        "肉蛋奶": ["猪肉", "牛肉", "羊肉", "鸡肉", "鸭肉", "鸡蛋", "鸭蛋", "牛奶",
                   "酸奶", "奶酪", "黄油", "培根", "火腿", "香肠", "鱼", "虾", "蟹",
                   "贝类", "鱿鱼", "腊肉", "排骨", "五花肉", "瘦肉", "鸡胸", "鸡腿"],

        "主食": ["大米", "小米", "糯米", "黑米", "糙米", "面粉", "面条", "米粉",
                 "粉丝", "年糕", "面包", "馒头", "包子", "饺子皮", "馄饨皮", "粥",
                 "燕麦", "麦片", "玉米面", "红薯粉"],

        "调料": ["盐", "糖", "酱油", "生抽", "老抽", "醋", "料酒", "蚝油", "香油",
                 "麻油", "辣椒油", "花椒油", "豆瓣酱", "甜面酱", "黄豆酱", "番茄酱",
                 "沙拉酱", "花生酱", "芝麻酱", "味精", "鸡精", "五香粉", "胡椒粉",
                 "辣椒粉", "花椒粉", "孜然粉", "咖喱粉", "姜", "蒜", "葱", "香菜",
                 "八角", "桂皮", "香叶", "干辣椒", "花椒"],

        "水果": ["苹果", "香蕉", "橙子", "橘子", "梨", "桃", "李", "杏", "葡萄",
                 "草莓", "蓝莓", "西瓜", "哈密瓜", "芒果", "猕猴桃", "火龙果",
                 "柠檬", "柚子", "红枣", "枸杞"],
    }

    def __init__(self):
        self.pantry: Dict[str, PantryItem] = {}
        self._load()

    def _load(self) -> None:
        """从文件加载库存"""
        try:
            with open(self.STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for name, item_data in data.items():
                    self.pantry[name] = PantryItem(**item_data)
        except (FileNotFoundError, json.JSONDecodeError):
            self.pantry = {}

    def _save(self) -> None:
        """保存库存到文件"""
        try:
            data = {name: asdict(item) for name, item in self.pantry.items()}
            with open(self.STORAGE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] 已保存到 {self.STORAGE_FILE}: {len(data)} 种食材")
        except Exception as e:
            print(f"保存库存失败: {e}")

    def _get_category(self, name: str) -> str:
        """判断食材类别"""
        for category, items in self.CATEGORY_MAP.items():
            for item in items:
                if item == name or item in name or name in item:
                    return category
        return "其他"

    def add_item(self, name: str, quantity: float, unit: str, expiry_date: Optional[str] = None,
                 mode: str = "add") -> None:
        """
        添加或更新库存

        参数:
            mode: "add" - 累加数量, "set" - 覆盖数量
        """
        name = name.strip()
        if name in self.pantry:
            if mode == "set":
                # 覆盖模式：直接设置新数量
                self.pantry[name].quantity = quantity
            else:
                # 累加模式：增加数量
                self.pantry[name].quantity += quantity

            if expiry_date:
                self.pantry[name].expiry_date = expiry_date
        else:
            self.pantry[name] = PantryItem(
                name=name,
                quantity=quantity,
                unit=unit,
                expiry_date=expiry_date,
                category=self._get_category(name)
            )
        self._save()

    # 添加 clear_all 方法
    def clear_all(self) -> None:
        """清空所有库存"""
        self.pantry.clear()
        self._save()
        print("[冰箱] clear_all 执行完毕")  # 调试输出

    def remove_item(self, name: str, quantity: Optional[float] = None) -> bool:
        """使用/减少库存，返回是否成功"""
        name = name.strip()
        if name not in self.pantry:
            return False

        if quantity is None or quantity >= self.pantry[name].quantity:
            # 全部用完，删除
            del self.pantry[name]
        else:
            self.pantry[name].quantity -= quantity

        self._save()
        return True

    def check_has(self, name: str, needed_quantity: float = 1) -> bool:
        """检查是否有足够库存"""
        name = name.strip()
        if name not in self.pantry:
            return False
        return self.pantry[name].quantity >= needed_quantity

    def get_all_items(self) -> List[Dict]:
        """获取所有库存列表"""
        return [asdict(item) for item in self.pantry.values()]

    def get_expiring_items(self, days: int = 3) -> List[Dict]:
        """获取即将过期的食材"""
        expiring = []
        today = datetime.now().date()

        for item in self.pantry.values():
            if item.expiry_date:
                try:
                    expiry = datetime.fromisoformat(item.expiry_date).date()
                    days_left = (expiry - today).days
                    if 0 <= days_left <= days:
                        expiring.append(asdict(item))
                except ValueError:
                    pass
        return expiring

    def filter_by_stock(self, recipes: List, threshold: float = 0.5) -> List:
        """
        根据库存筛选/排序菜谱
        返回评分，库存匹配度高的排前面
        """
        scored_recipes = []

        for recipe in recipes:
            ingredients = recipe.ingredients if hasattr(recipe, 'ingredients') else recipe.get('ingredients', {})

            # 计算库存匹配度
            total = len(ingredients)
            if total == 0:
                continue

            in_stock = sum(1 for ing in ingredients.keys() if self.check_has(ing))
            match_rate = in_stock / total

            if match_rate >= threshold:
                scored_recipes.append((match_rate, recipe))

        # 按匹配度降序排序
        scored_recipes.sort(key=lambda x: x[0], reverse=True)
        return [recipe for _, recipe in scored_recipes]

    def deduct_from_shopping_list(self, shopping_dict: Dict[str, str]) -> Dict[str, str]:
        """
        从购物清单中扣除已有库存
        返回还需要购买的食材清单
        """
        result = {}

        for ingredient, qty_str in shopping_dict.items():
            # 检查是否有库存
            if self.check_has(ingredient):
                result[ingredient] = qty_str  # 简化：仍需显示，但会标注已拥有
            else:
                result[ingredient] = qty_str

        return result

    def get_summary(self) -> str:
        """获取库存摘要"""
        if not self.pantry:
            return "冰箱里暂无食材记录。\n\n你可以说：「我家有鸡蛋、西红柿、葱」来添加库存。"

        # 按分类分组
        by_category = defaultdict(list)
        for item in self.pantry.values():
            qty_str = f"{item.quantity:.0f}" if item.quantity == int(item.quantity) else f"{item.quantity:.1f}"
            by_category[item.category].append(f"{item.name} {qty_str}{item.unit}")

        lines = ["## 🧊 当前冰箱库存\n"]
        for category, items in by_category.items():
            if items:
                lines.append(f"**{category}**：{', '.join(items)}")

        # 过期提醒
        expiring = self.get_expiring_items()
        if expiring:
            lines.append("\n### ⚠️ 即将过期的食材")
            for item in expiring:
                lines.append(f"- {item['name']}（{item['expiry_date']}到期）")

        return "\n".join(lines)

        # 按分类分组
        by_category = defaultdict(list)
        for item in self.pantry.values():
            # 格式化数量
            qty_str = f"{item.quantity:.0f}" if item.quantity == int(item.quantity) else f"{item.quantity:.1f}"
            by_category[item.category].append(f"{item.name} {qty_str}{item.unit}")

        lines = ["## 🧊 当前冰箱库存\n"]
        for category, items in by_category.items():
            if items:
                lines.append(f"**{category}**：{', '.join(items)}")

        # 过期提醒
        expiring = self.get_expiring_items()
        if expiring:
            lines.append("\n### ⚠️ 即将过期的食材")
            for item in expiring:
                lines.append(f"- {item['name']}（{item['expiry_date']}到期）")

        return "\n".join(lines)

    def parse_user_input(self, text: str) -> Tuple[List[Dict], str]:
        """
        使用大模型解析用户的自然语言库存输入

        返回: (items, action)
            items: [{"name": "鸡蛋", "quantity": 10, "unit": "个"}, ...]
            action: "add" | "set" | "remove" | "clear"
        """
        try:
            result = parse_pantry_input_with_llm(text)
            action = result.get("action", "add")
            items = result.get("items", [])

            # 过滤无效 item
            valid_items = [item for item in items if item.get("name")]

            return valid_items, action

        except PantryParseError as e:
            print(f"大模型解析失败，使用正则降级: {e}")
            # 降级到正则解析
            items = parse_pantry_input_fallback(text)
            return items, "add"