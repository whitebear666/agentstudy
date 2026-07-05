"""文件读写工具模块。

作用：
    提供最小化的 JSON/文本读写封装，统一输出目录创建和 UTF-8 编码。

关联模块：
    agent.py 使用它读取菜谱、写菜单和购物清单。
    agent_controller.py 使用它写偏好和生成结果。
"""

# tools.py
import json
from pathlib import Path
from typing import Any, Dict

class ToolError(Exception):
    pass

class ReadJsonTool:
    def run(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise ToolError(f"File not found: {path}")
        return json.loads(p.read_text(encoding="utf-8"))

class WriteTextTool:
    def run(self, path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote: {path}"

class WriteJsonTool:
    def run(self, path: str, data: Any) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"wrote: {path}"
