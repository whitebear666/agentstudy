# agent_controller.py
from __future__ import annotations

import copy
import json
from typing import Dict, Any, List

from agent import GroceryMealAgent
from conversation import ConversationState
from intent import detect_intent
from prefs_extractor import extract_prefs_update_with_qwen, PrefsExtractError
from tools import WriteJsonTool


HELP_TEXT = (
    "你可以用自然语言描述需求，我会记住并可多轮修改。\n\n"
    "示例：\n"
    " - 帮我规划三天\n"
    " - 两个人\n"
    " - 预算150，不要香菜，清淡点\n"
    " - 生成\n\n"
    "指令：\n"
    " - 生成 / 开始：生成 meal_plan 与 shopping_list\n"
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

        # 撤销栈：保存更新前的状态快照
        self._undo_stack: List[ConversationState] = []

    def reset(self) -> str:
        self.state = ConversationState()
        self._undo_stack.clear()
        return "已重置本次会话。你可以重新描述需求。"

    def undo(self) -> str:
        if not self._undo_stack:
            return "没有可以撤销的操作。"
        self.state = self._undo_stack.pop()
        return "已撤销上一条更新。\n" + self.show_prefs()

    def show_prefs(self) -> str:
        prefs_dict = _prefs_to_dict(self.state.prefs)
        return "当前偏好如下：\n" + json.dumps(prefs_dict, ensure_ascii=False, indent=2)

    def _format_next_step_hint(self) -> str:
        qs = _missing_questions(self.state)
        if not qs:
            return "已确认关键信息。你可以继续补充（预算/忌口/口味），或直接说“生成”。"
        return "我还需要你确认：\n- " + "\n- ".join(qs)

    def _update_prefs_from_text(self, text: str) -> str:
        try:
            partial = extract_prefs_update_with_qwen(text, retries=1)

            # 更新前压栈，支持撤销
            self._undo_stack.append(copy.deepcopy(self.state))

            self.state.update_from_partial(partial)
            return "我记住了。\n" + self._format_next_step_hint()
        except PrefsExtractError:
            return "我记住了。你可以继续补充人数/天数/预算/忌口/口味；确认好后对我说“生成”。"

    def generate(self) -> str:
        qs = _missing_questions(self.state)
        if qs:
            return "在生成前，我还需要确认一下：\n- " + "\n- ".join(qs)

        prefs = self.state.prefs

        prefs_dict = _prefs_to_dict(prefs)
        self.write_json.run("output/prefs.json", prefs_dict)

        self.agent.run(prefs)

        return (
            "生成完成。请查看输出文件：\n"
            "- output/prefs.json\n"
            "- output/meal_plan.md\n"
            "- output/shopping_list.json\n\n"
            "如果你想调整，比如“改成5天/不要香菜/换成川菜”，直接继续说即可，然后再说“生成”。"
        )

    def handle_user_message(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "请输入你的需求。"

        self.state.history.append({"role": "user", "content": text})

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