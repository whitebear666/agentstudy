from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, messagebox

from agent import GroceryMealAgent
from models import UserPrefs


HELP_TEXT = (
    "你可以这样输入：\n"
    "1) 2人 3天 家常 忌口:香菜\n"
    "2) 1人 2天\n"
    "3) 3天 预算150 忌口:辣椒 香菜\n\n"
    "当前版本：用简单规则解析（可继续升级为 LLM 对话理解）。"
)


def parse_user_message(text: str) -> UserPrefs:
    """
    简易解析：从用户输入里提取 people/days/budget/avoid/cuisine
    这是UI版MVP：先能用，后面再用LLM替换解析。
    """
    people = 2
    days = 3
    budget = None
    cuisine = "家常"
    avoid = []

    t = text.strip()

    # 天数：匹配“3天”
    import re
    m = re.search(r"(\d+)\s*天", t)
    if m:
        days = int(m.group(1))

    # 人数：匹配“2人”
    m = re.search(r"(\d+)\s*人", t)
    if m:
        people = int(m.group(1))

    # 预算：匹配“预算150”
    m = re.search(r"预算\s*(\d+(\.\d+)?)", t)
    if m:
        budget = float(m.group(1))

    # 忌口：匹配“忌口:香菜 辣椒”
    m = re.search(r"忌口[:：]\s*(.+)$", t)
    if m:
        avoid = [x for x in m.group(1).replace("，", " ").split() if x.strip()]

    # 菜系：简单判断（你也可以扩展）
    if "川菜" in t:
        cuisine = "川菜"
    elif "粤菜" in t:
        cuisine = "粤菜"
    elif "家常" in t:
        cuisine = "家常"

    return UserPrefs(
        people=people,
        days=days,
        budget=budget,
        avoid=avoid if avoid else None,
        cuisine=cuisine,
        has_kitchen=True,
    )


class ChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("买菜/食谱规划 Agent - 对话框 MVP")

        self.agent = GroceryMealAgent()

        # 聊天记录区（可滚动）
        self.chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=90, height=24)
        self.chat.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.chat.configure(state="disabled")

        # 输入框
        self.entry = tk.Entry(root, width=80)
        self.entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda event: self.on_send())

        # 发送按钮
        self.send_btn = tk.Button(root, text="发送", command=self.on_send, width=12)
        self.send_btn.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="e")

        # 菜单：帮助
        menubar = tk.Menu(root)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="输入示例", command=lambda: messagebox.showinfo("输入示例", HELP_TEXT))
        menubar.add_cascade(label="帮助", menu=helpmenu)
        root.config(menu=menubar)

        # 让窗口可伸缩
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self._append("Agent", "你好！告诉我人数/天数/预算/忌口，我来生成食谱和购物清单。")

    def _append(self, who: str, msg: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{who}: {msg}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def on_send(self) -> None:
        user_text = self.entry.get().strip()
        if not user_text:
            return
        self.entry.delete(0, tk.END)

        self._append("你", user_text)

        try:
            prefs = parse_user_message(user_text)
            self.agent.run(prefs)
            reply = (
                f"已生成 {prefs.days} 天（{prefs.people}人）食谱与购物清单。\n"
                "请查看：\n"
                "- output/meal_plan.md\n"
                "- output/shopping_list.json"
            )
            self._append("Agent", reply)
        except Exception as e:
            self._append("Agent", f"出错了：{e}")


def main():
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()