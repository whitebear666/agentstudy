"""预算约束模块。

作用：
    根据购物清单估算总价，判断是否超预算，并给出可替换的省钱建议。

关联模块：
    agent_controller.py 在生成购物清单后调用本模块。
    skills/shopping_list_optimizer.py 提供带价格的结构化购物清单。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class BudgetSuggestion:
    original_item: str
    original_price: float
    suggested_item: str
    suggested_price: float
    savings: float
    reason: str


class BudgetEnforcerSkill:
    REPLACEMENT_SUGGESTIONS = {
        "牛肉": ("鸡肉", 22.0, "牛肉换成鸡肉，蛋白质相近但更便宜"),
        "羊肉": ("猪肉", 28.0, "羊肉换成猪肉，价格更低"),
        "虾": ("豆腐", 5.0, "虾换成豆腐，保留蛋白质来源"),
        "鱼": ("鸡蛋", 1.0, "鱼换成鸡蛋，价格更低"),
        "排骨": ("瘦肉", 25.0, "排骨换成瘦肉"),
        "五花肉": ("瘦肉", 25.0, "五花肉换成瘦肉，更健康也更便宜"),
        "西兰花": ("白菜", 2.5, "西兰花换成白菜"),
        "鲍鱼": ("金针菇", 8.0, "鲍鱼换成金针菇"),
        "香菇": ("金针菇", 8.0, "香菇换成金针菇"),
    }

    def check_budget(
        self,
        shopping_list: Dict[str, float],
        budget: float,
        strict: bool = True,
    ) -> Tuple[bool, float, List[BudgetSuggestion]]:
        total = sum(shopping_list.values())
        if total <= budget:
            return False, 0.0, []

        over_amount = total - budget
        return True, over_amount, self._generate_suggestions(shopping_list, over_amount)

    def _generate_suggestions(
        self,
        shopping_list: Dict[str, float],
        over_amount: float,
    ) -> List[BudgetSuggestion]:
        suggestions: List[BudgetSuggestion] = []
        saved = 0.0

        for name, price in sorted(shopping_list.items(), key=lambda x: x[1], reverse=True):
            if saved >= over_amount:
                break
            if name not in self.REPLACEMENT_SUGGESTIONS:
                continue

            suggested_name, suggested_price, reason = self.REPLACEMENT_SUGGESTIONS[name]
            savings = price - suggested_price
            if savings <= 0:
                continue

            suggestions.append(
                BudgetSuggestion(
                    original_item=name,
                    original_price=price,
                    suggested_item=suggested_name,
                    suggested_price=suggested_price,
                    savings=savings,
                    reason=reason,
                )
            )
            saved += savings

        return suggestions

    def optimize_shopping_list(
        self,
        shopping_list: Dict[str, float],
        budget: float,
        apply_suggestions: bool = True,
    ) -> Tuple[Dict[str, float], List[BudgetSuggestion], float]:
        total = sum(shopping_list.values())
        if total <= budget:
            return shopping_list, [], total

        _, _, suggestions = self.check_budget(shopping_list, budget)
        if not suggestions or not apply_suggestions:
            return shopping_list, suggestions, total

        optimized = shopping_list.copy()
        applied: List[BudgetSuggestion] = []

        for suggestion in suggestions:
            if suggestion.original_item not in optimized:
                continue
            del optimized[suggestion.original_item]
            optimized[suggestion.suggested_item] = suggestion.suggested_price
            applied.append(suggestion)
            if sum(optimized.values()) <= budget:
                break

        return optimized, applied, sum(optimized.values())

    def suggest_meal_adjustments(
        self,
        meals: List[Dict],
        total_price: float,
        budget: float,
        target_saving: float,
    ) -> List[Dict]:
        suggestions = []
        saved = 0.0

        priced_meals = sorted(
            (meal for meal in meals if meal.get("price", 0) > 0),
            key=lambda x: x.get("price", 0),
            reverse=True,
        )

        for meal in priced_meals:
            if saved >= target_saving:
                break
            price = meal.get("price", 0)
            suggestions.append(
                {
                    "meal_name": meal.get("name", "未知"),
                    "current_price": price,
                    "suggestion": "可以考虑删除此菜品或替换成更便宜的食材",
                    "potential_saving": price,
                }
            )
            saved += price

        return suggestions

    def render_budget_report(
        self,
        total_price: float,
        budget: float,
        suggestions: List[BudgetSuggestion],
        is_over: bool,
    ) -> str:
        if not is_over:
            return "\n".join(
                [
                    "### 预算充足",
                    f"- 预算: {budget}",
                    f"- 预计总价: {total_price}",
                    f"- 剩余: {budget - total_price}",
                ]
            )

        lines = [
            "### 预算超支",
            f"- 预算: {budget}",
            f"- 预计总价: {total_price}",
            f"- 超出: {total_price - budget}",
        ]

        if suggestions:
            lines.append("")
            lines.append("#### 省钱建议")
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(
                    f"{i}. {suggestion.original_item} -> {suggestion.suggested_item}, "
                    f"节省 {suggestion.savings:.2f}: {suggestion.reason}"
                )

        return "\n".join(lines)
