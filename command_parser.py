"""Qwen 命令解析模块。

作用：
    将用户自然语言转换成 command_schema.Command。Qwen 不可用时抛出
    CommandParseError，让 agent_controller.py 回退到本地 intent 规则。

关联模块：
    llm_qwen.py 提供 Qwen 客户端。
    prompts.py 提供 COMMAND_PARSE_SYSTEM。
    command_schema.py 定义 Command。
    agent_controller.py 调用本模块。
"""

from __future__ import annotations

import json

from command_schema import Command
from llm_qwen import get_qwen_client, QwenAPIError
from prompts import COMMAND_PARSE_SYSTEM


class CommandParseError(Exception):
    pass


def parse_command_with_qwen(user_text: str, retries: int = 1) -> Command:
    try:
        client = get_qwen_client()
    except QwenAPIError as e:
        raise CommandParseError(str(e)) from e

    last_err: Exception | None = None

    for _ in range(retries + 1):
        try:
            raw = client.generate(
                prompt=f"用户输入：{user_text}",
                system=COMMAND_PARSE_SYSTEM,
                temperature=0.0,
            ).strip()

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise CommandParseError(f"Model output is not a JSON object: {raw}")

            return Command.from_dict(data)

        except Exception as e:
            last_err = e

    raise CommandParseError(f"Failed to parse command. Last error: {last_err}")
