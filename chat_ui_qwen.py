# chat_ui_qwen.py
from __future__ import annotations

import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dataclasses import asdict

from agent import GroceryMealAgent
from prefs_extractor import extract_prefs_with_qwen, PrefsExtractError
from models import UserPrefs
from tools import WriteJsonTool


HELP_TEXT = (
    "输入示例：\n"
    "1) 我们2个人，规划3天，预算150，别放香菜，想吃清淡点\n"
    "2) 1人 2天 忌口:辣椒\n"
    "3) 三天家常菜，不要牛奶和花生\n\n"
    "工作流：\n"
    "1) 先点【解析需求】→ 让 AI 抽取参数并展示\n"
    "2) 再点【生成计划】→ 生成 output/meal_plan.md & output/shopping_list.json\n"
)


class ChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("买菜/食谱规划 Agent（Qwen-Turbo）")

        self.agent = GroceryMealAgent()
        self.write_json = WriteJsonTool()

        self.last_prefs: UserPrefs | None = None

        # 聊天记录区
        self.chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=92, height=24)
        self.chat.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.chat.configure(state="disabled")

        # 输入框
        self.entry = tk.Entry(root)
        self.entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda event: self.on_parse())

        # 按钮：解析需求
        self.parse_btn = tk.Button(root, text="解析需求", command=self.on_parse, width=12)
        self.parse_btn.grid(row=1, column=1, padx=(0, 6), pady=(0, 10), sticky="e")

        # 按钮：生成计划
        self.gen_btn = tk.Button(root, text="生成计划", command=self.on_generate, width=12)
        self.gen_btn.grid(row=1, column=2, padx=(0, 10), pady=(0, 10), sticky="e")

        # 菜单
        menubar = tk.Menu(root)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="输入示例/帮助", command=lambda: messagebox.showinfo("帮助", HELP_TEXT))
        menubar.add_cascade(label="帮助", menu=helpmenu)
        root.config(menu=menubar)

        # 可伸缩
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self._append("Agent", "你好！先输入需求，然后点【解析需求】。确认无误后再点【生成计划】。")

    def _append(self, who: str, msg: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{who}: {msg}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def on_parse(self) -> None:
        user_text = self.entry.get().strip()
        if not user_text:
            self._append("Agent", "请先在输入框描述你的需求，然后点【解析需求】。")
            return

        self._append("你", user_text)
        self._append("Agent", "收到，我正在用 Qwen-Turbo 解析需求…")

        try:
            prefs = extract_prefs_with_qwen(user_text, retries=1)
            self.last_prefs = prefs

            prefs_dict = {
                "people": prefs.people,
                "days": prefs.days,
                "budget": prefs.budget,
                "avoid": prefs.avoid or [],
                "cuisine": prefs.cuisine,
                "has_kitchen": prefs.has_kitchen,
            }

            # 展示解析结果（可读）
            pretty = json.dumps(prefs_dict, ensure_ascii=False, indent=2)
            self._append("Agent", "解析完成。请确认以下参数是否正确：\n" + pretty)
            self._append("Agent", "如果正确请点【生成计划】；不正确就换句话再点【解析需求】。")
        except PrefsExtractError as e:
            self.last_prefs = None
            self._append("Agent", f"解析失败：{e}\n建议简化描述，例如：2人 3天 预算150 忌口 香菜 清淡。")
        except Exception as e:
            self.last_prefs = None
            self._append("Agent", f"运行出错：{e}")

    def on_generate(self) -> None:
        if not self.last_prefs:
            self._append("Agent", "还没有可用的解析结果。请先输入需求并点【解析需求】。")
            return

        prefs = self.last_prefs
        self._append("Agent", f"开始生成计划：{prefs.days}天 / {prefs.people}人 / {prefs.cuisine} …")

        try:
            # 记录本次参数（便于复现/答辩）
            prefs_dict = {
                "people": prefs.people,
                "days": prefs.days,
                "budget": prefs.budget,
                "avoid": prefs.avoid or [],
                "cuisine": prefs.cuisine,
                "has_kitchen": prefs.has_kitchen,
            }
            self.write_json.run("output/prefs.json", prefs_dict)

            # 生成 meal plan & shopping list
            self.agent.run(prefs)

            self._append(
                "Agent",
                "生成完成。请查看输出文件：\n"
                "- output/prefs.json\n"
                "- output/meal_plan.md\n"
                "- output/shopping_list.json",
            )
        except Exception as e:
            self._append("Agent", f"生成出错：{e}")


def main():
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()