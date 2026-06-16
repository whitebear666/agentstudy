# skills/shopping_list_optimizer.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict

from skills.price_fetcher import PriceFetcher, PriceInfo


class ShoppingListOptimizer:
    """
    购物清单优化器：将平铺的食材清单分类、量化、估价。
    支持实时价格获取（API/爬虫/用户输入/默认值）
    """

    # 食材分类字典（同上，略）
    CATEGORY_MAP = {...}  # 保持之前的内容

    def __init__(self, price_fetcher: Optional[PriceFetcher] = None):
        self.price_fetcher = price_fetcher or PriceFetcher()
        self.user_price_callback: Optional[Callable] = None

    def set_user_price_callback(self, callback: Callable[[str], Optional[float]]):
        """设置用户价格输入回调函数"""
        self.user_price_callback = callback

    def _get_category(self, ingredient: str) -> str:
        """判断食材属于哪个分类（同上）"""
        # ... 保持之前的内容

    def _parse_quantity(self, ingredient: str, qty_str: str) -> Tuple[float, str]:
        """
        解析数量字符串，返回 (数值, 单位)
        不在这里计算价格，价格由 price_fetcher 单独获取
        """
        qty_str = qty_str.strip()

        import re
        match = re.match(r'(\d+(?:\.\d+)?)\s*(\D*)', qty_str)
        if match:
            num = float(match.group(1))
            unit = match.group(2).strip() or "份"
            return (num, unit)

        return (1, "份")

    def optimize(
            self,
            shopping_dict: Dict[str, str],
            budget: Optional[float] = None,
            force_refresh_price: bool = False
    ) -> Dict:
        """
        优化购物清单

        参数:
            shopping_dict: {"食材名": "数量", ...}
            budget: 用户预算（可选）
            force_refresh_price: 是否强制刷新价格（忽略缓存）

        返回:
            结构化的购物清单
        """
        # 分类统计
        categorized: Dict[str, List[Dict]] = defaultdict(list)
        total_price = 0.0

        # 批量获取价格
        ingredients = list(shopping_dict.keys())
        price_infos = self.price_fetcher.get_prices_batch(
            ingredients,
            user_callback=self.user_price_callback,
            force_refresh=force_refresh_price
        )

        for ingredient, qty_str in shopping_dict.items():
            category = self._get_category(ingredient)
            num, unit = self._parse_quantity(ingredient, qty_str)

            # 获取价格信息
            price_info = price_infos.get(ingredient)
            if price_info:
                unit_price = price_info.price
                source = price_info.source
                store = price_info.store
            else:
                unit_price = 5.0
                source = "unknown"
                store = "未知"

            # 根据单位计算价格
            if unit in ["g", "克"]:
                item_price = unit_price * (num / 500)  # 以500g为基准
            elif unit in ["kg", "公斤"]:
                item_price = unit_price * (num * 2)
            elif unit in ["个", "只", "根", "把"]:
                item_price = unit_price * num
            else:
                item_price = unit_price

            categorized[category].append({
                "name": ingredient,
                "qty": f"{num:.0f}" if num == int(num) else f"{num:.1f}",
                "unit": unit,
                "unit_price": round(unit_price, 2),
                "estimated_price": round(item_price, 2),
                "price_source": source,
                "store": store
            })
            total_price += item_price

        # 构建结果
        result = dict(categorized)

        # 添加统计信息
        total_items = sum(len(items) for items in categorized.values())
        result["统计"] = dict(总项目数=total_items, 预估总价=round(total_price, 2),
                              价格更新时间=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if budget is not None:
            result["统计"]["预算"] = budget
            result["统计"]["剩余"] = round(budget - total_price, 2)
            result["统计"]["是否超支"] = total_price > budget

        # 确保分类顺序固定
        ordered_result = {}
        for cat in ["蔬菜", "肉蛋奶", "主食", "调料", "水果", "其他"]:
            if cat in result:
                ordered_result[cat] = result[cat]
        ordered_result["统计"] = result["统计"]

        return ordered_result

    def to_markdown(self, optimized: Dict) -> str:
        """将优化后的购物清单转换为 Markdown 格式"""
        lines = ["# 🛒 购物清单\n"]

        for category, items in optimized.items():
            if category == "统计" or category == "预算报告":
                continue
            if not items:
                continue

            lines.append(f"## {category}\n")
            lines.append("| 食材 | 数量 | 单价(元) | 预估价格 |")
            lines.append("|------|------|----------|----------|")
            for item in items:
                lines.append(
                    f"| {item['name']} | {item['qty']}{item['unit']} | "
                    f"¥{item['unit_price']} | ¥{item['estimated_price']} |"
                )
            lines.append("")

        # 统计信息
        stats = optimized.get("统计", {})
        lines.append("## 📊 统计信息\n")
        lines.append(f"- 总项目数：{stats.get('总项目数', 0)}")
        lines.append(f"- 预估总价：¥{stats.get('预估总价', 0)}")
        lines.append(f"- 价格更新时间：{stats.get('价格更新时间', '未知')}")

        if '预算' in stats:
            lines.append(f"- 预算：¥{stats['预算']}")
            lines.append(f"- 预算剩余：¥{stats['剩余']}")
            if stats.get('是否超支'):
                lines.append("- ⚠️ 预算超支！可以考虑替换掉一些高价食材")

        # 如果有预算报告，添加进去
        if "预算报告" in optimized:
            lines.append("\n" + optimized["预算报告"])

        lines.append("\n---\n")
        lines.append("**说明**：价格为模拟参考价，实际购买请以当地市场为准。")

        return "\n".join(lines)
