"""Qwen 对话 UI 模块。

作用：
    提供 Tkinter 聊天窗口，是当前推荐的在线入口。用户在这里输入自然
    语言需求，系统会通过 AgentController 处理并展示回复。

关联模块：
    agent_controller.py 负责所有业务逻辑。
    command_parser.py、prefs_extractor.py 会间接调用 Qwen API。
    llm_qwen.py 负责 Qwen API 客户端和 key 读取。
"""

# chat_ui_qwen.py
from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, messagebox

from agent_controller import AgentController


HELP_TEXT = (
    "使用方法：\n"
    "1) 直接用自然语言描述需求，我会记住。\n"
    "2) 随时可以说“当前偏好/参数”查看。\n"
    "3) 说“生成/开始”生成输出文件。\n"
    "4) 说“撤销/undo”撤销上一条更新。\n"
    "5) 说“重置/reset”清空会话。\n\n"
    "示例：\n"
    " - 帮我规划三天\n"
    " - 两个人\n"
    " - 预算150，不要香菜，清淡点\n"
    " - 生成\n"
)


class ChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("买菜/食谱规划 Agent（Qwen-Turbo）")

        self.controller = AgentController()

        self.chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=92, height=26)
        self.chat.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.chat.configure(state="disabled")

        self.entry = tk.Entry(root)
        self.entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda event: self.on_send())

        self.send_btn = tk.Button(root, text="发送", command=self.on_send, width=12)
        self.send_btn.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="e")

        menubar = tk.Menu(root)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="帮助/示例", command=lambda: messagebox.showinfo("帮助", HELP_TEXT))
        menubar.add_cascade(label="帮助", menu=helpmenu)
        root.config(menu=menubar)

        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self._append("Agent", "你好！直接描述需求即可；说“生成”会输出计划；说“帮助”查看示例。")

    def _append(self, who: str, msg: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{who}: {msg}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def _append_placeholder(self, who: str, msg: str) -> str:
        """
        插入一条可更新的占位消息，返回一个 tag id。
        """
        tag = f"placeholder_{id(self)}_{self.chat.index(tk.END)}"
        self.chat.configure(state="normal")
        start = self.chat.index(tk.END)
        self.chat.insert(tk.END, f"{who}: {msg}\n\n")
        end = self.chat.index(tk.END)
        self.chat.tag_add(tag, start, end)
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)
        return tag

    def _replace_placeholder(self, tag: str, who: str, msg: str) -> None:
        self.chat.configure(state="normal")
        ranges = self.chat.tag_ranges(tag)
        if ranges:
            start, end = ranges[0], ranges[1]
            self.chat.delete(start, end)
            self.chat.insert(start, f"{who}: {msg}\n\n")
            # 重新标记（范围会变）
            new_end = self.chat.index(f"{start} lineend + 2c")
            self.chat.tag_remove(tag, "1.0", tk.END)
            self.chat.tag_add(tag, start, tk.END)
        else:
            # 万一 tag 不存在就 fallback append
            self.chat.insert(tk.END, f"{who}: {msg}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def on_send(self) -> None:
        user_text = self.entry.get().strip()
        if not user_text:
            return
        self.entry.delete(0, tk.END)

        self._append("你", user_text)

        # 占位：处理中…
        ph = self._append_placeholder("Agent", "处理中…")

        try:
            reply = self.controller.handle_user_message(user_text)
            self._replace_placeholder(ph, "Agent", reply)
        except Exception as e:
            self._replace_placeholder(ph, "Agent", f"运行出错：{e}")


def main():
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
