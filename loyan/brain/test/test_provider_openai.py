"""测试 OpenAI 兼容提供商连通性

使用前设置环境变量:
    export TEST_API_KEY=sk-xxx
    export TEST_API_BASE=https://api.xxx.com/v1/
    export TEST_MODEL=gpt-4o-mini

用法:
    python -m loyan.brain.test.test_provider_openai
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from loyan.brain.provider.types.openai import OpenAIProvider


async def main():
    api_key = os.environ.get("TEST_API_KEY", "")
    api_base = os.environ.get("TEST_API_BASE", "https://api.openai.com/v1/")
    model = os.environ.get("TEST_MODEL", "gpt-4o-mini")

    if not api_key:
        print(" 请设置 TEST_API_KEY 环境变量")
        sys.exit(1)

    provider = OpenAIProvider({"api_key": api_key, "api_base": api_base})
    await provider.open()
    print(f" Provider: {provider.name}")
    print(f"  API Base: {provider.api_base}")
    print(f"  Model: {model}")

    reply = await provider.chat(
        messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
        model=model,
    )
    print(f" Chat: {reply[:80]}...")

    count = 0
    async for chunk in provider.chat_stream(
        messages=[{"role": "user", "content": "数到3"}],
        model=model,
    ):
        count += len(chunk)
    print(f" Stream: {count} chars")

    await provider.close()
    print(" Done")


if __name__ == "__main__":
    asyncio.run(main())
