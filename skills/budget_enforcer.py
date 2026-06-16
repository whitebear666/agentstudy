# skills/budget_enforcer.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BudgetSuggestion:
    """预算优化建议"""
    original_item: str
    original_price: float
    suggested_item: str
    suggested_price: float
    savings: float
    reason: str


class BudgetEnforcerSkill:
    """
    预算硬约束技能：
    - 检查购物清单是否超预算
    - 提供替换建议（换更便宜的食材）
    - 自动优化菜单
    """

    # 食材替换映射（高价食材 -> 低价替代品）
    REPLACEMENT_SUGGESTIONS = {
        "牛肉": ("鸡肉", 22.0, "牛肉换成鸡肉，蛋白质相当但更便宜"),
        "羊肉": ("猪肉", 28.0, "羊肉换成猪肉"),
        "虾": ("豆腐", 5.0, "虾换成豆腐，同样高蛋白"),
        "鱼": ("鸡蛋", 1.0, "鱼换成鸡蛋，营养不减"),
        "排骨": ("瘦肉", 25.0, "排骨换成瘦肉"),
        "五花肉": ("瘦肉", 25.0, "五花肉换成瘦肉，更健康便宜"),
        "西兰花": ("白菜", 2.5, "西兰花换成白菜"),
        "蘑菇": ("金针菇", 8.0, "蘑菇换成金针菇"),
        "香菇": ("金针菇", 8.0, "香菇换成金针菇"),
        "对虾": ("豆腐", 5.0, "虾换成豆腐"),
        "鲤鱼": ("鸡蛋", 1.0, "鱼换成鸡蛋"),
    }

    # 可删除的配菜（优先级最低）
    DISPENSABLE_ITEMS = ["配菜", "汤", "小菜"]

    def __init__(self):
        pass

    def check_budget(
            self,
            shopping_list: Dict[str, float],  # {食材名: 价格}
            budget: float,
            strict: bool = True
    ) -> Tuple[bool, float, List[BudgetSuggestion]]:
        """
        检查是否超预算

        返回: (是否超预算, 超出金额, 建议列表)
        """
        total = sum(shopping_list.values())

        if total <= budget:
            return (False, 0.0, [])

        over_amount = total - budget

        # 生成优化建议
        suggestions = self._generate_suggestions(shopping_list, over_amount)

        return (True, over_amount, suggestions)

    def _generate_suggestions(
            self,
            shopping_list: Dict[str, float],
            over_amount: float
    ) -> List[BudgetSuggestion]:
        """生成预算优化建议"""
        suggestions = []

        # 按价格从高到低排序
        sorted_items = sorted(shopping_list.items(), key=lambda x: x[1], reverse=True)

        saved = 0
        for name, price in sorted_items:
            if saved >= over_amount:
                break

            # 检查是否有替代品
            if name in self.REPLACEMENT_SUGGESTIONS:
                suggested_name, suggested_price, reason = self.REPLACEMENT_SUGGESTIONS[name]
                savings = price - suggested_price

                if savings > 0:
                    suggestions.append(BudgetSuggestion(
                        original_item=name,
                        original_price=price,
                        suggested_item=suggested_name,
                        suggested_price=suggested_price,
                        savings=savings,
                        reason=reason
                    ))
                    saved += savings

        return suggestions

    def optimize_shopping_list(
            self,
            shopping_list: Dict[str, float],
            budget: float,
            apply_suggestions: bool = True
    ) -> Tuple[Dict[str, float], List[BudgetSuggestion], float]:
        """
        优化购物清单以适应预算

        返回: (优化后的清单, 应用的建议, 新总价)
        """
        if sum(shopping_list.values()) <= budget:
            return shopping_list, [], sum(shopping_list.values())

        # 获取建议
        _, over_amount, suggestions = self.check_budget(shopping_list, budget)

        if not suggestions:
            return shopping_list, [], sum(shopping_list.values())

        # 应用建议
        optimized = shopping_list.copy()
        applied = []
        saved = 0

        for sugg in suggestions:
            if sugg.original_item in optimized:
                # 移除原食材
                del optimized[sugg.original_item]
                # 添加替代食材
                optimized[sugg.suggested_item] = sugg.suggested_price
                applied.append(sugg)
                saved += sugg.savings

                # 检查是否已达标
                if sum(optimized.values()) <= budget:
                    break

        return optimized, applied, sum(optimized.values())

    def suggest_meal_adjustments(
            self,
            meals: List[Dict],  # 每餐的菜品列表
            total_price: float,
            budget: float,
            target_saving: float
    ) -> List[Dict]:
        """
        建议调整菜品（删减或替换）
        """
        suggestions = []

        # 按价格排序
        priced_meals = []
        for meal in meals:
            if meal.get('price', 0) > 0:
                priced_meals.append(meal)

        priced_meals.sort(key=lambda x: x.get('price', 0), reverse=True)

        saved = 0
        for meal in priced_meals:
            if saved >= target_saving:
                break

            suggestions.append({
                "meal_name": meal.get('name', '未知'),
                "current_price": meal.get('price', 0),
                "suggestion": "可以考虑删除此菜品或换成更便宜的",
                "potential_saving": meal.get('price', 0)
            })
            saved += meal.get('price', 0)

        return suggestions

    def render_budget_report(
            self,
            total_price: float,
            budget: float,
            suggestions: List[BudgetSuggestion],
            is_over: bool
    ) -> str:
        """生成预算报告 Markdown"""
        lines = []

        if not is_over:
            lines.append(f"### ✅ 预算充足\n")
            lines.append(f"- **预算**：¥{budget}")
            lines.append(f"- **预估总价**：¥{total_price}")
            lines.append(f"- **剩余**：¥{budget - total_price}")
            return "\n".join(lines)

        lines.append(f"### ⚠️ 预算超支\n")
        lines.append(f"- **预算**：¥{budget}")
        lines.append(f"- **预估总价**：¥{total_price}")
        lines.append(f"- **超出**：¥{total_price - budget}")

        if suggestions:
            lines.append(f"\n#### 💡 省钱建议\n")
            for i, sugg in enumerate(suggestions, 1):
                lines.append(f"{i}. **{sugg.original_item}** (¥{sugg.original_price})")
                lines.append(f"   → 换成 **{sugg.suggested_item}** (¥{sugg.suggested_price})")
                lines.append(f"   → 节省 ¥{sugg.savings}")
                lines.append(f"   → {sugg.reason}\n")

            total_saving = sum(s.savings for s in suggestions)
            lines.append(f"\n**预计可节省**：¥{total_saving}")
            if total_saving >= total_price - budget:
                lines.append(f"✅ 采纳以上建议后，总价将降至 ¥{total_price - total_saving}，符合预算！")

        return "\n".join(lines)# skills/budget_enforcer.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BudgetSuggestion:
    """预算优化建议"""
    original_item: str
    original_price: float
    suggested_item: str
    suggested_price: float
    savings: float
    reason: str


class BudgetEnforcerSkill:
    """
    预算硬约束技能：
    - 检查购物清单是否超预算
    - 提供替换建议（换更便宜的食材）
    - 自动优化菜单
    """

    # 食材替换映射（高价食材 -> 低价替代品）
    REPLACEMENT_SUGGESTIONS = {
        "牛肉": ("鸡肉", 22.0, "牛肉换成鸡肉，蛋白质相当但更便宜"),
        "羊肉": ("猪肉", 28.0, "羊肉换成猪肉"),
        "虾": ("豆腐", 5.0, "虾换成豆腐，同样高蛋白"),
        "鱼": ("鸡蛋", 1.0, "鱼换成鸡蛋，营养不减"),
        "排骨": ("瘦肉", 25.0, "排骨换成瘦肉"),
        "五花肉": ("瘦肉", 25.0, "五花肉换成瘦肉，更健康便宜"),
        "西兰花": ("白菜", 2.5, "西兰花换成白菜"),
        "蘑菇": ("金针菇", 8.0, "蘑菇换成金针菇"),
        "香菇": ("金针菇", 8.0, "香菇换成金针菇"),
        "对虾": ("豆腐", 5.0, "虾换成豆腐"),
        "鲤鱼": ("鸡蛋", 1.0, "鱼换成鸡蛋"),
    }

    # 可删除的配菜（优先级最低）
    DISPENSABLE_ITEMS = ["配菜", "汤", "小菜"]

    def __init__(self):
        pass

    def check_budget(
        self,
        shopping_list: Dict[str, float],  # {食材名: 价格}
        budget: float,
        strict: bool = True
    ) -> Tuple[bool, float, List[BudgetSuggestion]]:
        """
        检查是否超预算

        返回: (是否超预算, 超出金额, 建议列表)
        """
        total = sum(shopping_list.values())

        if total <= budget:
            return (False, 0.0, [])

        over_amount = total - budget

        # 生成优化建议
        suggestions = self._generate_suggestions(shopping_list, over_amount)

        return (True, over_amount, suggestions)

    def _generate_suggestions(
        self,
        shopping_list: Dict[str, float],
        over_amount: float
    ) -> List[BudgetSuggestion]:
        """生成预算优化建议"""
        suggestions = []

        # 按价格从高到低排序
        sorted_items = sorted(shopping_list.items(), key=lambda x: x[1], reverse=True)

        saved = 0
        for name, price in sorted_items:
            if saved >= over_amount:
                break

            # 检查是否有替代品
            if name in self.REPLACEMENT_SUGGESTIONS:
                suggested_name, suggested_price, reason = self.REPLACEMENT_SUGGESTIONS[name]
                savings = price - suggested_price

                if savings > 0:
                    suggestions.append(BudgetSuggestion(
                        original_item=name,
                        original_price=price,
                        suggested_item=suggested_name,
                        suggested_price=suggested_price,
                        savings=savings,
                        reason=reason
                    ))
                    saved += savings

        return suggestions

    def optimize_shopping_list(
        self,
        shopping_list: Dict[str, float],
        budget: float,
        apply_suggestions: bool = True
    ) -> Tuple[Dict[str, float], List[BudgetSuggestion], float]:
        """
        优化购物清单以适应预算

        返回: (优化后的清单, 应用的建议, 新总价)
        """
        if sum(shopping_list.values()) <= budget:
            return shopping_list, [], sum(shopping_list.values())

        # 获取建议
        _, over_amount, suggestions = self.check_budget(shopping_list, budget)

        if not suggestions:
            return shopping_list, [], sum(shopping_list.values())

        # 应用建议
        optimized = shopping_list.copy()
        applied = []
        saved = 0

        for sugg in suggestions:
            if sugg.original_item in optimized:
                # 移除原食材
                del optimized[sugg.original_item]
                # 添加替代食材
                optimized[sugg.suggested_item] = sugg.suggested_price
                applied.append(sugg)
                saved += sugg.savings

                # 检查是否已达标
                if sum(optimized.values()) <= budget:
                    break

        return optimized, applied, sum(optimized.values())

    def suggest_meal_adjustments(
        self,
        meals: List[Dict],  # 每餐的菜品列表
        total_price: float,
        budget: float,
        target_saving: float
    ) -> List[Dict]:
        """
        建议调整菜品（删减或替换）
        """
        suggestions = []

        # 按价格排序
        priced_meals = []
        for meal in meals:
            if meal.get('price', 0) > 0:
                priced_meals.append(meal)

        priced_meals.sort(key=lambda x: x.get('price', 0), reverse=True)

        saved = 0
        for meal in priced_meals:
            if saved >= target_saving:
                break

            suggestions.append({
                "meal_name": meal.get('name', '未知'),
                "current_price": meal.get('price', 0),
                "suggestion": "可以考虑删除此菜品或换成更便宜的",
                "potential_saving": meal.get('price', 0)
            })
            saved += meal.get('price', 0)

        return suggestions

    def render_budget_report(
        self,
        total_price: float,
        budget: float,
        suggestions: List[BudgetSuggestion],
        is_over: bool
    ) -> str:
        """生成预算报告 Markdown"""
        lines = []

        if not is_over:
            lines.append(f"### ✅ 预算充足\n")
            lines.append(f"- **预算**：¥{budget}")
            lines.append(f"- **预估总价**：¥{total_price}")
            lines.append(f"- **剩余**：¥{budget - total_price}")
            return "\n".join(lines)

        lines.append(f"### ⚠️ 预算超支\n")
        lines.append(f"- **预算**：¥{budget}")
        lines.append(f"- **预估总价**：¥{total_price}")
        lines.append(f"- **超出**：¥{total_price - budget}")

        if suggestions:
            lines.append(f"\n#### 💡 省钱建议\n")
            for i, sugg in enumerate(suggestions, 1):
                lines.append(f"{i}. **{sugg.original_item}** (¥{sugg.original_price})")
                lines.append(f"   → 换成 **{sugg.suggested_item}** (¥{sugg.suggested_price})")
                lines.append(f"   → 节省 ¥{sugg.savings}")
                lines.append(f"   → {sugg.reason}\n")

            total_saving = sum(s.savings for s in suggestions)
            lines.append(f"\n**预计可节省**：¥{total_saving}")
            if total_saving >= total_price - budget:
                lines.append(f"✅ 采纳以上建议后，总价将降至 ¥{total_price - total_saving}，符合预算！")

        return "\n".join(lines)