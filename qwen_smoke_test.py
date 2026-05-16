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