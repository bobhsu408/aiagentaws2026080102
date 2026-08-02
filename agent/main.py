"""Agent 進入點

啟動 Strands Agent，載入 career tools，接受使用者對話。

使用方式：
    # 本地測試
    python -m agent.main

    # AgentCore 部署後由 runtime 呼叫此模組
"""

import os
from pathlib import Path

from strands import Agent
from strands.models.bedrock import BedrockModel

from .tools import TOOL_REGISTRY
from .prompts.system_prompt import SYSTEM_PROMPT


def create_model() -> BedrockModel:
    """建立 Bedrock 模型實例"""
    model_id = os.environ.get(
        "BEDROCK_MODEL_ID",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    )
    region = os.environ.get("AWS_REGION", "us-west-2")

    return BedrockModel(
        model_id=model_id,
        region_name=region,
    )


def create_agent() -> Agent:
    """建立並回傳 Agent 實例"""
    model = create_model()

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOL_REGISTRY,
    )

    return agent


# AgentCore runtime 會找這個變數
agent = create_agent()


if __name__ == "__main__":
    # 本地互動測試
    print("=== 職涯導航家 Agent（本地模式）===")
    print("輸入 'quit' 離開\n")

    test_agent = create_agent()
    while True:
        user_input = input("你：")
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        response = test_agent(user_input)
        print(f"\nAgent：{response}\n")
