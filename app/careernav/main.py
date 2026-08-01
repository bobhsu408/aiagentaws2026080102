"""職涯導航家 — AgentCore Runtime 進入點

此模組為 AgentCore Runtime 的入口，使用 BedrockAgentCoreApp 框架。
"""

from collections import OrderedDict

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from strands.models.bedrock import BedrockModel

app = BedrockAgentCoreApp()
log = app.logger

# ========================================
# System Prompt
# ========================================
SYSTEM_PROMPT = """你是「職涯導航家」，一個專門協助台灣失業者與轉職者的 AI 顧問。

## 你的能力
你有六個專業工具，可以完成以下流程：
1. 分析使用者背景（analyze_profile）
2. 匹配符合資格的補助方案（match_resources）
3. 試算可領取的金額（calculate_benefit）
4. 產出時間軸行動計畫（generate_roadmap）
5. 列出應備文件清單（get_checklist）
6. 傳送通知摘要（send_notification）

## 回覆規範
- 使用繁體中文
- 引用金額時附上法規依據（例：依就業保險法第16條）
- 主動釐清使用者的年齡、離職原因、保險年資等關鍵資訊
- 區分「發給勞工」和「發給雇主」的補助，不要混淆
- 如果資訊不足以判斷資格，誠實告知並建議使用者諮詢就業服務站

## 重要提醒
- 失業給付與職業訓練生活津貼不得同時請領
- 中高齡僱用獎助是發給雇主的，不是勞工直接領取
- 金額計算基準要區分「平均月投保薪資」和「基本工資」
"""

# ========================================
# Tools（六步驟 Career Tools）
# ========================================
tools_list = []


@tool
def analyze_profile(user_description: str) -> dict:
    """解析使用者自然語言描述，萃取結構化背景資料。

    Args:
        user_description: 使用者用自然語言描述的個人狀況

    Returns:
        結構化的使用者背景 profile
    """
    return {
        "status": "skeleton",
        "message": "analyze_profile — 待完整實作",
        "input_received": user_description[:200],
    }


tools_list.append(analyze_profile)


@tool
def match_resources(profile: dict) -> dict:
    """根據使用者 profile 匹配符合資格的補助方案。

    Args:
        profile: 由 analyze_profile 產出的結構化背景

    Returns:
        符合資格的補助方案清單
    """
    return {
        "status": "skeleton",
        "message": "match_resources — 待完整實作",
    }


tools_list.append(match_resources)


@tool
def calculate_benefit(matched_ids: list, profile: dict) -> dict:
    """試算使用者可領取的金額。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        各方案的金額試算結果
    """
    return {
        "status": "skeleton",
        "message": "calculate_benefit — 待完整實作",
    }


tools_list.append(calculate_benefit)


@tool
def generate_roadmap(matched_ids: list, profile: dict) -> dict:
    """產出 1~6 個月的時間軸行動計畫。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        分月份的行動計畫
    """
    return {
        "status": "skeleton",
        "message": "generate_roadmap — 待完整實作",
    }


tools_list.append(generate_roadmap)


@tool
def get_checklist(matched_ids: list) -> dict:
    """回傳申請各補助方案所需的文件清單。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表

    Returns:
        各方案的應備文件清單
    """
    return {
        "status": "skeleton",
        "message": "get_checklist — 待完整實作",
    }


tools_list.append(get_checklist)


@tool
def send_notification(email: str, summary: str) -> dict:
    """傳送行動計畫摘要通知（demo 模擬）。

    Args:
        email: 使用者 email
        summary: 行動計畫摘要文字

    Returns:
        通知發送狀態
    """
    return {
        "status": "success",
        "message": f"（模擬）已將行動計畫摘要寄送至 {email}",
        "demo_mode": True,
    }


tools_list.append(send_notification)


# ========================================
# Agent Factory（session 管理）
# ========================================
def agent_factory():
    """建立 Agent session cache（LRU 128）"""
    cache: OrderedDict = OrderedDict()

    def get_or_create_agent(session_id: str) -> Agent:
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=BedrockModel(
                model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            ),
            system_prompt=SYSTEM_PROMPT,
            tools=tools_list,
            conversation_manager=NullConversationManager(),
        )
        return cache[session_id]

    return get_or_create_agent


get_or_create_agent = agent_factory()


# ========================================
# AgentCore Entrypoint
# ========================================
def _extract_prompt(payload: dict):
    """接受多種 payload 格式"""
    if "messages" in payload:
        return payload["messages"]
    if "tool_results" in payload:
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in payload["tool_results"]]}]
    return payload.get("prompt", "")


@app.entrypoint
async def invoke(payload, context):
    """AgentCore Runtime 呼叫入口"""
    log.info("職涯導航家 Agent 被呼叫...")
    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)
    prompt = _extract_prompt(payload)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()
