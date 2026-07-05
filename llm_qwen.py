"""Qwen API 客户端和 key 读取模块。

作用：
    封装 DashScope/Qwen HTTP 请求，并按顺序从环境变量、Windows 用户/
    系统环境变量、项目 .env、当前目录 .env、用户目录 .qwen.env 中读取
    API key。

关联模块：
    command_parser.py 和 prefs_extractor.py 调用 get_qwen_client()。
    scripts/check_qwen_key.py 使用诊断函数检查 key 是否可见。
    qwen_smoke_test.py 使用本模块验证真实 API 调用。
"""

# llm_qwen.py
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class QwenAPIError(Exception):
    pass


KEY_NAMES = ["QWEN_API_KEY", "DASHSCOPE_API_KEY", "ALIYUN_API_KEY"]
PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass
class QwenClient:
    api_key: str
    model: str = "qwen-turbo"
    base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2,
                 response_format: Optional[dict] = None) -> str:
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
            payload.setdefault("parameters", {})
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


def _candidate_dotenv_paths() -> List[Path]:
    paths = [
        PROJECT_ROOT / ".env",
        Path.cwd() / ".env",
        Path.home() / ".qwen.env",
    ]
    unique: List[Path] = []
    for path in paths:
        if path not in unique:
            unique.append(path)
    return unique


def _read_dotenv_key(names: List[str]) -> Optional[str]:
    for env_path in _candidate_dotenv_paths():
        key = _read_key_from_file(env_path, names)
        if key:
            return key
    return None


def _read_key_from_file(env_path: Path, names: List[str]) -> Optional[str]:
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() in names:
            value = value.strip().strip('"').strip("'")
            if value:
                return value
    return None


def _read_windows_env_key(names: List[str]) -> Optional[str]:
    if os.name != "nt":
        return None

    try:
        import winreg
    except Exception:
        return None

    locations = [
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    for hive, subkey in locations:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                for name in names:
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                    except FileNotFoundError:
                        continue
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except OSError:
            continue
    return None


def _get_env_key(names: List[str]) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value

    value = _read_windows_env_key(names)
    if value:
        return value

    return _read_dotenv_key(names)


def get_qwen_client() -> QwenClient:
    key = _get_env_key(KEY_NAMES)
    if not key:
        raise QwenAPIError("Missing env var QWEN_API_KEY (also tried DASHSCOPE_API_KEY and .env)")
    return QwenClient(api_key=key)


def qwen_key_diagnostics() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for name in KEY_NAMES:
        value = os.getenv(name)
        results.append(
            {
                "source": f"process env:{name}",
                "found": bool(value),
                "length": len(value) if value else 0,
            }
        )

    if os.name == "nt":
        for name in KEY_NAMES:
            value = _read_windows_env_key([name])
            results.append(
                {
                    "source": f"windows env:{name}",
                    "found": bool(value),
                    "length": len(value) if value else 0,
                }
            )

    for env_path in _candidate_dotenv_paths():
        for name in KEY_NAMES:
            value = _read_key_from_file(env_path, [name])
            results.append(
                {
                    "source": f"{env_path}:{name}",
                    "found": bool(value),
                    "length": len(value) if value else 0,
                }
            )

    return results
