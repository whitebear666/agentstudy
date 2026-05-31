# llm_qwen.py
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class QwenAPIError(Exception):
    pass


@dataclass
class QwenClient:
    api_key: str
    model: str = "qwen-turbo"
    base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> str:
        """
        Minimal text generation call.
        Returns the generated text (best-effort).
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # DashScope 通常使用 prompt / messages 之一。这里用 messages 形式更接近 chat。
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {"temperature": temperature},
        }
        if response_format is not None:
            payload["parameters"]["response_format"] = response_format

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as e:
            raise QwenAPIError(f"HTTP request failed: {e}")

        try:
            obj = json.loads(raw)
        except Exception:
            raise QwenAPIError(f"Non-JSON response: {raw[:2000]}")

        # best-effort parse
        if "output" not in obj:
            raise QwenAPIError(f"Unexpected response: {obj}")

        output = obj["output"]
        # 常见字段：output.text 或 output.choices[0].message.content
        if isinstance(output, dict) and "text" in output and isinstance(output["text"], str):
            return output["text"].strip()

        if isinstance(output, dict) and "choices" in output and output["choices"]:
            msg = output["choices"][0].get("message", {})
            content = msg.get("content")
            if isinstance(content, str):
                return content.strip()

        raise QwenAPIError(f"Cannot extract text from response: {obj}")


def get_qwen_client() -> QwenClient:
    key = os.getenv("QWEN_API_KEY")
    if not key:
        raise QwenAPIError("Missing env var QWEN_API_KEY")
    return QwenClient(api_key=key)