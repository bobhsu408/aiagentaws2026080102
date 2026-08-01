"""職涯導航家 — AgentCore Runtime 進入點

此模組為 AgentCore Runtime 的入口，使用 BedrockAgentCoreApp 框架。
六步驟 Career Tools 已抽離至 tools/ 套件，資料檔位於 data/。
"""

import os
import sys
from collections import OrderedDict

# 確保以 entrypoint 方式執行時，本目錄在 import 路徑上，
# 讓 `from tools import ...` 這類絕對 import 穩定可用。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from strands.models.bedrock import BedrockModel

from tools.career_tools import TOOL_REGISTRY

app = BedrockAgentCoreApp()
log = app.logger

# ========================================
# System Prompt
# ========================================
SYSTEM_PROMPT = """你是「職涯導航家」，一個專門協助台灣失業者與轉職者的 AI 顧問。

## 你的六步驟服務流程
依使用者情況，善用以下六個工具循序協助（不必每次全用，但盡量走完能給出完整計畫）：
1. analyze_profile — 解析使用者背景。若回傳的 missing_fields 有值，先主動追問這些關鍵資訊，再往下走。
2. match_resources — 用整理好的 profile 匹配補助方案。留意 match_status：
   - eligible＝符合、likely＝符合但需確認行動意願（如是否願意受訓）、needs_info＝仍缺資料。
3. calculate_benefit — 試算金額。若回傳 needs_input，代表缺少投保薪資等數值，
   要向使用者說明「這是以基本工資估的保守下限」，並邀請提供實際投保薪資以精算。
4. generate_roadmap — 產出 1~6 個月行動計畫。課程分兩類：curated（計畫層級穩定資料）
   與 hint（即時搜尋關鍵字）；若有即時搜尋能力，可據 keywords 補充當期開課資訊。
5. get_checklist — 彙整應備文件，區分通用與各方案專用。
6. send_notification — 使用者要求時，模擬寄送行動計畫摘要（展示模式）。

## 回覆規範
- 一律使用繁體中文，語氣溫暖、具同理心，面對的是失業或轉職中的人。
- 引用金額時附上法規依據（工具回傳的 law_references 有條號與連結，請據實引用）。
- 主動釐清年齡、離職原因、就業保險年資等判斷資格的關鍵資訊。
- 明確區分「發給勞工」與「發給雇主」的補助，不要讓使用者誤以為雇主獎助是自己能領的。
- 資訊不足以判斷時，誠實告知，並建議就近洽詢公立就業服務站。

## 重要事實提醒（避免給錯建議）
- 失業給付與職業訓練生活津貼「不得同時請領」，需擇一。
- 失業給付：年滿 45 歲或持身心障礙證明者，請領上限由 6 個月延長為 9 個月；有受扶養眷屬可加給。
- 中高齡僱用獎助是發給「雇主」的誘因，不是勞工直接領取。
- 金額基準要分清「平均月投保薪資」與「基本工資」，兩者計算結果差異很大。
- 產業新尖兵計畫限 15~29 歲青年，不要推薦給中高齡使用者。
"""

# ========================================
# Agent Factory（session 管理，LRU 128）
# ========================================
def agent_factory():
    """建立 Agent session cache（LRU 128）。"""
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
            tools=TOOL_REGISTRY,
            conversation_manager=NullConversationManager(),
        )
        return cache[session_id]

    return get_or_create_agent


get_or_create_agent = agent_factory()


# ========================================
# AgentCore Entrypoint
# ========================================
def _extract_prompt(payload: dict):
    """接受多種 payload 格式。"""
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
    """AgentCore Runtime 呼叫入口。"""
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
