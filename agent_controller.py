# agent_controller.py
from __future__ import annotations

import copy
import json
from command_parser import parse_command_with_qwen, CommandParseError
from typing import Dict, Any, List, Optional

from agent import GroceryMealAgent
from conversation import ConversationState
from intent import detect_intent
from prefs_extractor import extract_prefs_update_with_qwen, PrefsExtractError
from tools import WriteJsonTool
from skills.meal_replace import MealReplaceSkill
from models import DayPlan, MealSet

HELP_TEXT = (
    "你可以用自然语言描述需求，我会记住并可多轮修改。\n\n"
    "示例：\n"
    " - 帮我规划三天\n"
    " - 两个人\n"
    " - 预算150，不要香菜，清淡点\n"
    " - 生成\n\n"
    "指令：\n"
    " - 生成 / 开始：生成 meal_plan 与 shopping_list\n"
    " - 替换 / 换菜：例如「把第2天的晚餐主菜换成清淡的」\n"
    " - 当前偏好 / 参数：查看我记住的内容\n"
    " - 撤销 / undo：撤销上一条更新\n"
    " - 重置：清空本次会话\n"
)


def _prefs_to_dict(prefs) -> Dict[str, Any]:
    return {
        "people": prefs.people,
        "days": prefs.days,
        "budget": prefs.budget,
        "avoid": prefs.avoid or [],
        "cuisine": prefs.cuisine,
        "has_kitchen": prefs.has_kitchen,
        "breakfast_style": getattr(prefs, "breakfast_style", None),
        "lunch_style": getattr(prefs, "lunch_style", None),
        "dinner_style": getattr(prefs, "dinner_style", None),
    }


def _missing_questions(state: ConversationState) -> List[str]:
    questions: List[str] = []
    if "people" not in state.confirmed_fields:
        questions.append("请问几个人吃？例如：2个人")
    if "days" not in state.confirmed_fields:
        questions.append("请问要规划几天？例如：3天")
    return questions


class AgentController:
    def __init__(self):
        self.state = ConversationState()
        self.agent = GroceryMealAgent()
        self.write_json = WriteJsonTool()
        self.replace_skill = MealReplaceSkill()

        # 撤销栈：保存更新前的状态快照
        self._undo_stack: List[ConversationState] = []

        # 存储最近一次生成的菜单和购物清单（用于替换操作）
        self.current_day_plans: List[DayPlan] = []
        self.current_shopping: Dict[str, str] = {}
        self.current_prefs = None  # 存储生成时的偏好快照

    def reset(self) -> str:
        self.state = ConversationState()
        self._undo_stack.clear()
        self.current_day_plans = []
        self.current_shopping = {}
        self.current_prefs = None
        return "已重置本次会话。你可以重新描述需求。"

    def undo(self) -> str:
        if not self._undo_stack:
            return "没有可以撤销的操作。"
        self.state = self._undo_stack.pop()
        return "已撤销上一条更新。\n" + self.show_prefs()

    def show_prefs(self) -> str:
        prefs_dict = _prefs_to_dict(self.state.prefs)
        return "当前偏好如下：\n" + json.dumps(prefs_dict, ensure_ascii=False, indent=2)

    def show_current_menu(self) -> str:
        """显示当前已生成的菜单（如果有）"""
        if not self.current_day_plans:
            return "还没有生成菜单。请先说「生成」创建菜单。"
        return self.agent.show_current_menu(self.current_day_plans)

    def _format_next_step_hint(self) -> str:
        qs = _missing_questions(self.state)
        if not qs:
            return "已确认关键信息。你可以继续补充（预算/忌口/口味），或直接说生成。"
        return "我还需要你确认：\n- " + "\n- ".join(qs)

    def _update_prefs_from_text(self, text: str) -> str:
        try:
            partial = extract_prefs_update_with_qwen(text, retries=1)

            # 更新前压栈，支持撤销
            self._undo_stack.append(copy.deepcopy(self.state))

            self.state.update_from_partial(partial)
            return "我记住了。\n" + self._format_next_step_hint()
        except PrefsExtractError:
            return "我记住了。你可以继续补充人数/天数/预算/忌口/口味；确认好后对我说生成。"

    def generate(self) -> str:
        qs = _missing_questions(self.state)
        if qs:
            return "在生成前，我还需要确认一下：\n- " + "\n- ".join(qs)

        prefs = self.state.prefs

        prefs_dict = _prefs_to_dict(prefs)
        self.write_json.run("output/prefs.json", prefs_dict)

        # 调用修改后的 run 方法，获取返回的菜单数据
        plans, shopping = self.agent.run(prefs, save_output=True)

        # 存储当前菜单数据，供后续替换使用
        self.current_day_plans = plans
        self.current_shopping = shopping
        self.current_prefs = copy.deepcopy(prefs)

        # 生成简短的菜单预览
        preview = self.agent.show_current_menu(plans)

        return (
            "生成完成。请查看输出文件：\n"
            "- output/prefs.json\n"
            "- output/meal_plan.md\n"
            "- output/shopping_list.json\n\n"
            f"【当前菜单预览】\n{preview}\n\n"
            "如果你想调整某道菜，可以说：\n"
            "- 「把第2天的晚餐主菜换成清淡的」\n"
            "- 「把第1天的午餐主菜换成鱼」\n"
            "- 「查看当前菜单」\n\n"
            "确认好后再说「生成」会重新生成完整菜单。"
        )

    def replace_meal(
            self,
            day: int,
            meal_type: str,
            part_type: str = "main",
            constraint: Optional[str] = None
    ) -> str:
        """
        动态替换某一餐的某个部分。

        参数:
            day: 第几天（1-based）
            meal_type: "breakfast" | "lunch" | "dinner"
            part_type: "main" | "side" | "staple" | "soup"（默认 main）
            constraint: 约束条件，如"清淡的"、"鱼"、"肉"等
        """
        # 1. 检查是否有已生成的菜单
        if not self.current_day_plans:
            return "还没有生成菜单，请先说「生成」创建菜单后再进行替换。"

        # 2. 找到要替换的 DayPlan
        target_plan = None
        for plan in self.current_day_plans:
            if plan.day_index == day:
                target_plan = plan
                break

        if not target_plan:
            return f"未找到第 {day} 天的菜单。当前有 {len(self.current_day_plans)} 天的菜单。"

        # 3. 获取要替换的 MealSet
        meal_set = None
        if meal_type == "breakfast":
            meal_set = target_plan.breakfast
        elif meal_type == "lunch":
            meal_set = target_plan.lunch
        elif meal_type == "dinner":
            meal_set = target_plan.dinner
        else:
            return f"未知的餐次类型：{meal_type}，请使用 breakfast/lunch/dinner"

        if not meal_set:
            return f"第 {day} 天的 {meal_type} 菜单不存在。"

        # 4. 获取当前已用的菜名集合（避免同一天重复）
        used_names = set()
        for plan in self.current_day_plans:
            for mt in ['breakfast', 'lunch', 'dinner']:
                ms = getattr(plan, mt, None)
                if ms:
                    if ms.main:
                        used_names.add(ms.main.name)
                    if ms.side:
                        used_names.add(ms.side.name)
                    if ms.staple:
                        used_names.add(ms.staple.name)
                    if ms.soup:
                        used_names.add(ms.soup.name)

        # 5. 获取当前菜品对应的部分（如果已存在，也加入 used_names）
        old_meal = getattr(meal_set, part_type, None)
        if old_meal and old_meal.name in used_names:
            used_names.remove(old_meal.name)  # 允许替换成别的菜，但排除自己

        # 6. 调用 ReplaceMealSkill 获取新菜
        avoid = self.state.prefs.avoid if self.state.prefs else None

        new_meal = self.replace_skill.replace_meal_part(
            recipe_db=self.agent.recipe_db,
            recipe_meta=self.agent.recipe_meta,
            part_type=part_type,
            constraint=constraint,
            avoid=avoid,
            used_names=used_names,
        )

        if not new_meal:
            constraint_msg = f"符合「{constraint}」要求的" if constraint else ""
            return f"抱歉，没有找到{constraint_msg}{part_type}菜品。请换个要求试试，比如「清淡的」「鱼」「肉类」等。"

        # 7. 记录旧菜名用于反馈
        old_name = old_meal.name if old_meal else "无"

        # 8. 更新 MealSet 中的对应部分
        setattr(meal_set, part_type, new_meal)

        # 9. 重新合并购物清单
        self._rebuild_shopping_list()

        # 10. 重新生成输出文件
        if self.current_prefs:
            md = self.agent.render_markdown(self.current_prefs, self.current_day_plans)
            self.agent.write_text.run("output/meal_plan.md", md)
            self.agent.write_json.run("output/shopping_list.json", self.current_shopping)

        # 11. 生成替换成功的反馈
        part_names = {
            "main": "主菜",
            "side": "配菜",
            "staple": "主食",
            "soup": "汤"
        }
        part_cn = part_names.get(part_type, part_type)
        meal_type_cn = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}.get(meal_type, meal_type)

        preview = self.agent.show_current_menu(self.current_day_plans)

        return (
            f"已将第 {day} 天的{meal_type_cn}的{part_cn}从「{old_name}」替换为「{new_meal.name}」。\n\n"
            f"【更新后的菜单预览】\n{preview}\n\n"
            f"已自动更新 output/meal_plan.md 和 output/shopping_list.json。"
        )

    def _rebuild_shopping_list(self) -> None:
        """根据当前菜单重新合并购物清单"""
        from models import MealSet

        need: Dict[str, str] = {}

        # 尝试加载冰箱数据
        try:
            fridge = self.agent.read_json.run("data/fridge.json")
            have_all = sum((fridge.get(cat, []) for cat in fridge.keys()), [])
        except Exception:
            have_all = []

        def add_mealset(ms: MealSet) -> None:
            if not ms:
                return
            for meal in [ms.main, ms.side, ms.staple, ms.soup]:
                if not meal:
                    continue
                for k, v in meal.ingredients.items():
                    if k in have_all:
                        continue
                    need[k] = "适量/按需"

        for dp in self.current_day_plans:
            add_mealset(dp.breakfast)
            add_mealset(dp.lunch)
            add_mealset(dp.dinner)

        self.current_shopping = need

    def handle_user_message(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "请输入你的需求。"

        self.state.history.append({"role": "user", "content": text})

        # 1) 优先：让大模型解析为"结构化命令"，能解析就直接执行
        try:
            cmd = parse_command_with_qwen(text, retries=1)

            # 有 updates 才入撤销栈（避免"完成/生成"也压栈）
            if cmd.updates and any(v is not None for v in cmd.updates.values()) or cmd.updates.get("avoid") == []:
                self._undo_stack.append(copy.deepcopy(self.state))
                self.state.update_from_partial(cmd.updates)

            if cmd.intent == "help":
                return HELP_TEXT
            if cmd.intent == "undo":
                return self.undo()
            if cmd.intent == "reset":
                return self.reset()
            if cmd.intent == "show_prefs":
                return self.show_prefs()
            if cmd.intent == "show_menu":
                return self.show_current_menu()
            if cmd.intent == "generate":
                return self.generate()
            if cmd.intent == "replace":
                # 处理替换命令
                return self._handle_replace_command(cmd)

            # update_prefs
            return "我记住了。\n" + self._format_next_step_hint()

        except CommandParseError:
            # 解析失败则回退旧逻辑
            pass

        # 2) 回退：旧 intent + prefs_update
        intent = detect_intent(text).type

        if intent == "help":
            return HELP_TEXT
        if intent == "undo":
            return self.undo()
        if intent == "reset":
            return self.reset()
        if intent == "show_prefs":
            return self.show_prefs()
        if intent == "generate":
            try:
                return self.generate()
            except Exception as e:
                return f"生成过程出错：{e}"

        return self._update_prefs_from_text(text)

    def _handle_replace_command(self, cmd) -> str:
        """
        处理替换命令，从解析出的命令中提取参数。
        cmd 应包含:
            - day: int (第几天)
            - meal_type: str (breakfast/lunch/dinner)
            - part_type: str (main/side/staple/soup，默认 main)
            - constraint: str (约束条件)
        """
        day = getattr(cmd, 'day', None)
        meal_type = getattr(cmd, 'meal_type', None)
        part_type = getattr(cmd, 'part_type', 'main')
        constraint = getattr(cmd, 'constraint', None)

        # 参数校验
        if day is None:
            return "请指定要替换第几天的菜，例如「把第2天的晚餐主菜换成清淡的」"

        if meal_type is None:
            return "请指定要替换哪一餐（早餐/午餐/晚餐）"

        # 支持中文输入转换
        meal_type_map = {
            "早餐": "breakfast",
            "午餐": "lunch",
            "晚餐": "dinner",
            "breakfast": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner",
        }
        meal_type = meal_type_map.get(meal_type, meal_type)

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return f"无法识别的餐次：{meal_type}，请使用 早餐/午餐/晚餐"

        # part_type 中文转换
        part_type_map = {
            "主菜": "main",
            "配菜": "side",
            "主食": "staple",
            "汤": "soup",
            "main": "main",
            "side": "side",
            "staple": "staple",
            "soup": "soup",
        }
        part_type = part_type_map.get(part_type, part_type)

        if part_type not in ["main", "side", "staple", "soup"]:
            part_type = "main"  # 默认替换主菜

        return self.replace_meal(day, meal_type, part_type, constraint)