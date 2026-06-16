# skills/nutrition_calculator.py
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from models import Meal, MealSet, DayPlan


@dataclass
class NutritionInfo:
    """营养信息"""
    calories: float = 0  # 热量（千卡）
    protein: float = 0  # 蛋白质（克）
    carbs: float = 0  # 碳水化合物（克）
    fat: float = 0  # 脂肪（克）

    def __add__(self, other: "NutritionInfo") -> "NutritionInfo":
        return NutritionInfo(
            calories=self.calories + other.calories,
            protein=self.protein + other.protein,
            carbs=self.carbs + other.carbs,
            fat=self.fat + other.fat
        )

    def to_dict(self) -> Dict:
        return {
            "calories": round(self.calories, 1),
            "protein": round(self.protein, 1),
            "carbs": round(self.carbs, 1),
            "fat": round(self.fat, 1)
        }


@dataclass
class MealNutrition:
    """一餐的营养信息"""
    total: NutritionInfo
    main: NutritionInfo
    side: Optional[NutritionInfo]
    staple: Optional[NutritionInfo]
    soup: Optional[NutritionInfo]


class NutritionCalculator:
    """
    营养计算器：
    - 计算每餐和全天的热量、蛋白质、碳水、脂肪
    - 根据健康目标评估
    - 推荐是否替换菜品
    """

    NUTRITION_DB_FILE = "data/nutrition_db.json"

    # 健康目标配置
    GOAL_CONFIG = {
        "减脂": {
            "daily_calories": 1500,
            "protein_ratio": 0.30,
            "carbs_ratio": 0.40,
            "fat_ratio": 0.30,
            "description": "低卡高蛋白，减少碳水化合物"
        },
        "增肌": {
            "daily_calories": 2500,
            "protein_ratio": 0.35,
            "carbs_ratio": 0.40,
            "fat_ratio": 0.25,
            "description": "高蛋白，适量碳水，充足热量"
        },
        "维持": {
            "daily_calories": 2000,
            "protein_ratio": 0.25,
            "carbs_ratio": 0.50,
            "fat_ratio": 0.25,
            "description": "均衡营养，适中热量"
        },
        "增重": {
            "daily_calories": 3000,
            "protein_ratio": 0.25,
            "carbs_ratio": 0.55,
            "fat_ratio": 0.20,
            "description": "高热量，充足碳水"
        }
    }

    def __init__(self):
        self.nutrition_db = self._load_db()

    def _load_db(self) -> Dict:
        """加载营养数据库"""
        try:
            with open(self.NUTRITION_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _parse_quantity(self, qty_str: str) -> Tuple[float, str]:
        """解析数量字符串，返回 (数值, 单位)"""
        qty_str = qty_str.strip()
        match = re.match(r'(\d+(?:\.\d+)?)\s*(\D*)', qty_str)
        if match:
            num = float(match.group(1))
            unit = match.group(2).strip() or "个"
            return (num, unit)
        return (1, "份")

    def _get_ingredient_nutrition(self, name: str, quantity: float, unit: str) -> NutritionInfo:
        """获取单个食材的营养信息"""
        # 查找食材
        for db_name, data in self.nutrition_db.items():
            if db_name == name or db_name in name or name in db_name:
                unit_weight = data.get("unit_weight", 100)
                data_unit = data.get("unit", "g")

                # 根据单位计算倍数
                if unit in ["g", "克"]:
                    ratio = quantity / unit_weight
                elif unit in ["kg", "公斤"]:
                    ratio = (quantity * 1000) / unit_weight
                elif unit in ["个", "只"]:
                    # 按个计算：每个的重量 = unit_weight
                    ratio = quantity * unit_weight / 100
                else:
                    ratio = 1

                return NutritionInfo(
                    calories=data.get("calories", 0) * ratio,
                    protein=data.get("protein", 0) * ratio,
                    carbs=data.get("carbs", 0) * ratio,
                    fat=data.get("fat", 0) * ratio
                )

        # 未找到，返回默认值
        return NutritionInfo()

    def calculate_meal_nutrition(self, meal: Meal) -> NutritionInfo:
        """计算单个菜品的营养"""
        total = NutritionInfo()

        for ingredient, qty_str in meal.ingredients.items():
            qty, unit = self._parse_quantity(qty_str)
            nutrition = self._get_ingredient_nutrition(ingredient, qty, unit)
            total += nutrition

        return total

    def calculate_mealset_nutrition(self, mealset: MealSet) -> MealNutrition:
        """计算一餐（主菜+配菜+主食+汤）的营养"""
        main_nut = self.calculate_meal_nutrition(mealset.main) if mealset.main else NutritionInfo()
        side_nut = self.calculate_meal_nutrition(mealset.side) if mealset.side else None
        staple_nut = self.calculate_meal_nutrition(mealset.staple) if mealset.staple else None
        soup_nut = self.calculate_meal_nutrition(mealset.soup) if mealset.soup else None

        total = main_nut
        if side_nut:
            total += side_nut
        if staple_nut:
            total += staple_nut
        if soup_nut:
            total += soup_nut

        return MealNutrition(
            total=total,
            main=main_nut,
            side=side_nut,
            staple=staple_nut,
            soup=soup_nut
        )

    def calculate_day_nutrition(self, day_plan: DayPlan) -> Dict[str, NutritionInfo]:
        """计算一天的总营养"""
        breakfast_nut = self.calculate_mealset_nutrition(day_plan.breakfast).total
        lunch_nut = self.calculate_mealset_nutrition(day_plan.lunch).total
        dinner_nut = self.calculate_mealset_nutrition(day_plan.dinner).total

        return {
            "breakfast": breakfast_nut,
            "lunch": lunch_nut,
            "dinner": dinner_nut,
            "total": breakfast_nut + lunch_nut + dinner_nut
        }

    def calculate_plan_nutrition(self, day_plans: List[DayPlan]) -> List[Dict]:
        """计算整个计划的营养"""
        results = []
        for day_plan in day_plans:
            day_nut = self.calculate_day_nutrition(day_plan)
            results.append({
                "day": day_plan.day_index,
                "breakfast": day_nut["breakfast"].to_dict(),
                "lunch": day_nut["lunch"].to_dict(),
                "dinner": day_nut["dinner"].to_dict(),
                "total": day_nut["total"].to_dict()
            })
        return results

    def evaluate_by_goal(self, total_nut: NutritionInfo, goal: str) -> Dict:
        """根据健康目标评估营养是否达标"""
        if goal not in self.GOAL_CONFIG:
            return {"status": "unknown", "message": f"未知目标：{goal}"}

        config = self.GOAL_CONFIG[goal]
        target_calories = config["daily_calories"]

        # 计算热量偏差
        actual_calories = total_nut.calories
        calorie_diff = actual_calories - target_calories
        calorie_status = "超标" if calorie_diff > 200 else "偏低" if calorie_diff < -200 else "达标"

        # 计算营养比例
        total_protein = total_nut.protein
        total_carbs = total_nut.carbs
        total_fat = total_nut.fat
        total_cals = total_nut.calories

        if total_cals > 0:
            protein_ratio = (total_protein * 4) / total_cals
            carbs_ratio = (total_carbs * 4) / total_cals
            fat_ratio = (total_fat * 9) / total_cals
        else:
            protein_ratio = carbs_ratio = fat_ratio = 0

        # 判断营养是否平衡
        target_protein = config["protein_ratio"]
        target_carbs = config["carbs_ratio"]
        target_fat = config["fat_ratio"]

        suggestions = []
        if protein_ratio < target_protein - 0.05:
            suggestions.append("蛋白质偏低，建议增加肉类、蛋类、豆制品")
        elif protein_ratio > target_protein + 0.05:
            suggestions.append("蛋白质偏高，可适当减少肉类")

        if actual_calories < target_calories - 300:
            suggestions.append(f"总热量偏低，目标{target_calories}kcal，建议增加主食")
        elif actual_calories > target_calories + 300:
            suggestions.append(f"总热量超标，目标{target_calories}kcal，建议减少高热量食物")

        # 检查碳水化合物
        if carbs_ratio > target_carbs + 0.1:
            suggestions.append("碳水化合物偏高，建议减少主食或选择粗粮")

        # 检查脂肪
        if fat_ratio > target_fat + 0.1:
            suggestions.append("脂肪偏高，建议减少油、肥肉")

        return {
            "goal": goal,
            "target_calories": target_calories,
            "actual_calories": round(actual_calories, 1),
            "calorie_status": calorie_status,
            "protein_ratio": round(protein_ratio * 100, 1),
            "carbs_ratio": round(carbs_ratio * 100, 1),
            "fat_ratio": round(fat_ratio * 100, 1),
            "target_protein_ratio": target_protein * 100,
            "target_carbs_ratio": target_carbs * 100,
            "target_fat_ratio": target_fat * 100,
            "suggestions": suggestions
        }

    def render_nutrition_markdown(self, day_plans: List[DayPlan], goal: Optional[str] = None) -> str:
        """生成营养报告的 Markdown"""
        nutrition_data = self.calculate_plan_nutrition(day_plans)

        lines = ["## 🥗 营养分析\n"]

        # 汇总表格
        lines.append("### 每日营养汇总\n")
        lines.append("| 天数 | 早餐(kcal) | 午餐(kcal) | 晚餐(kcal) | 合计(kcal) | 蛋白质(g) | 碳水(g) | 脂肪(g) |")
        lines.append("|------|-----------|-----------|-----------|-----------|----------|---------|---------|")

        for day in nutrition_data:
            total = day["total"]
            breakfast = day["breakfast"]
            lunch = day["lunch"]
            dinner = day["dinner"]
            lines.append(
                f"| Day {day['day']} | {breakfast['calories']} | {lunch['calories']} | {dinner['calories']} | "
                f"{total['calories']} | {total['protein']} | {total['carbs']} | {total['fat']} |"
            )

        lines.append("")

        # 健康目标评估
        if goal and goal in self.GOAL_CONFIG:
            # 计算总营养
            total_nut = NutritionInfo()
            for day in nutrition_data:
                total_nut.calories += day["total"]["calories"]
                total_nut.protein += day["total"]["protein"]
                total_nut.carbs += day["total"]["carbs"]
                total_nut.fat += day["total"]["fat"]

            # 平均每天
            avg_nut = NutritionInfo(
                calories=total_nut.calories / len(day_plans),
                protein=total_nut.protein / len(day_plans),
                carbs=total_nut.carbs / len(day_plans),
                fat=total_nut.fat / len(day_plans)
            )

            evaluation = self.evaluate_by_goal(avg_nut, goal)

            lines.append(f"### 🎯 健康目标：{goal}\n")
            lines.append(f"- **目标热量**：{evaluation['target_calories']} kcal/天")
            lines.append(f"- **实际热量**：{evaluation['actual_calories']} kcal/天")
            lines.append(f"- **热量状态**：{evaluation['calorie_status']}")
            lines.append(
                f"- **营养比例**：蛋白质 {evaluation['protein_ratio']}% / 碳水 {evaluation['carbs_ratio']}% / 脂肪 {evaluation['fat_ratio']}%")
            lines.append(
                f"- **目标比例**：蛋白质 {int(evaluation.get('target_protein_ratio', 25) * 100)}% / 碳水 {int(evaluation.get('target_carbs_ratio', 50) * 100)}% / 脂肪 {int(evaluation.get('target_fat_ratio', 25) * 100)}%")

            if evaluation.get('suggestions'):
                lines.append("\n**💡 建议**：")
                for suggestion in evaluation['suggestions']:
                    lines.append(f"- {suggestion}")
            lines.append("")

        # 如果没有健康目标，添加提示
        else:
            lines.append("### 💪 健康建议\n")
            lines.append("> 设置健康目标可获得个性化营养建议。")
            lines.append("> 例如：「我要减脂」、「想增肌」、「维持体重」\n")

        return "\n".join(lines)