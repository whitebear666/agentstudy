from __future__ import annotations

import json

from command_schema import Command
from llm_qwen import get_qwen_client
from prompts import COMMAND_PARSE_SYSTEM


class CommandParseError(Exception):
    pass


def parse_command_with_qwen(user_text: str, retries: int = 1) -> Command:
    client = get_qwen_client()
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