"""Qwen API 连通性测试脚本。

作用：
    手动验证项目是否能读取 key，并真正请求到 Qwen API。

关联模块：
    llm_qwen.py 提供 get_qwen_client()。
    scripts/check_qwen_key.py 用于只检查 key 可见性、不发起 API 请求。
"""

from llm_qwen import get_qwen_client

def main():
    client = get_qwen_client()
    out = client.generate(
        prompt="用一句话解释什么是智能体（AI Agent）。",
        system="你是一个简洁的中文助手，只输出一句话，不要换行。",
        temperature=0.2,
    )
    print(out)

if __name__ == "__main__":
    main()
