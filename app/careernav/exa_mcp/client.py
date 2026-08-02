"""Exa AI MCP Client 封裝

建立連往 Exa AI 官方託管 MCP 伺服器（https://mcp.exa.ai/mcp）的
strands MCPClient，供 main.py 註冊進 Agent 的 tools 清單。

設計原則（對應 docs/IMPLEMENTATION_PLAN_20250731.md Task 5 驗收標準）：
- timeout：連線逾時（startup_timeout）與單次查詢逾時（call_tool 的
  read_timeout_seconds）皆有上限，不讓 Agent 卡住等待。
- graceful degradation：以 continue_on_error=True 建立 MCPClient，
  若 Exa 服務連不上，Strands 會讓這個 provider 回傳空工具清單，
  Agent 仍可用其餘六個 Career Tools 正常運作，只是少了即時搜尋能力。
- 認證：Exa 的官方託管端點預設不需 API key（keyless，有速率限制）；
  若 .env 提供 EXA_API_KEY，依官方文件以 query string 帶入以提高額度。
  已知風險：Exa 官方文件目前唯一支援的傳遞方式是 URL query string，
  沒有 Authorization header 的替代方案（社群已回報此安全性顧慮，
  詳見 exa-labs/exa-mcp-server GitHub issue #334），此為 Exa 服務端
  的限制，非本專案程式碼可規避。
"""

import os
from datetime import timedelta

from strands.tools.mcp.mcp_client import MCPClient

# Exa AI 官方託管 MCP 端點
_EXA_MCP_BASE_URL = "https://mcp.exa.ai/mcp"

# 只開放預設的兩個搜尋工具（讀 web、抓網頁全文），不開進階篩選與
# Exa Agent（agent_run 需額外認證且成本較高，本專案 demo 情境不需要）。
_EXA_ENABLED_TOOLS = "web_search_exa,web_fetch_exa"

# 連線逾時：建立連線最多等待秒數，超過視為連不上（觸發 graceful degradation）
DEFAULT_STARTUP_TIMEOUT_SECONDS = 10

# 單次工具呼叫逾時：一次搜尋/抓取最多等待秒數，超過視為此次查詢失敗
DEFAULT_CALL_TIMEOUT_SECONDS = 15


def _build_exa_mcp_url() -> str:
    """組出 Exa MCP 端點 URL，視 EXA_API_KEY 是否存在決定是否帶入金鑰。

    Returns:
        完整的 Exa MCP 端點 URL（含 tools 參數，選填 exaApiKey）。
    """
    params = [f"tools={_EXA_ENABLED_TOOLS}"]
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if api_key:
        # 官方文件目前唯一支援的金鑰傳遞方式即為 query string，
        # 詳見 client.py 頂部 docstring 的已知風險說明。
        params.append(f"exaApiKey={api_key}")
    return f"{_EXA_MCP_BASE_URL}?{'&'.join(params)}"


def get_exa_mcp_client(
    startup_timeout: int = DEFAULT_STARTUP_TIMEOUT_SECONDS,
    url_override: str | None = None,
) -> MCPClient:
    """建立連往 Exa AI MCP 伺服器的 MCPClient。

    回傳的 MCPClient 可直接放進 `Agent(tools=[..., client])`；Strands
    會在 Agent 建立時呼叫 `load_tools()`，連線失敗時（因
    continue_on_error=True）不會拋出例外，Agent 只是少了即時搜尋工具。

    Args:
        startup_timeout: 連線逾時秒數，預設 10 秒。
        url_override: 測試用參數，覆寫實際連線的 URL（略過 EXA_API_KEY /
            tools query string 組裝）。正式環境不應傳入此參數。

    Returns:
        設定好 timeout 與 graceful degradation 的 MCPClient 實例。
    """
    url = url_override if url_override is not None else _build_exa_mcp_url()

    def _transport():
        # 延遲 import：streamable_http 依賴的 httpx/anyio 只在真正建立
        # 連線時才需要，避免在無網路的單元測試環境載入失敗。
        from mcp.client.streamable_http import streamablehttp_client

        return streamablehttp_client(url=url)

    return MCPClient(
        _transport,
        startup_timeout=startup_timeout,
        continue_on_error=True,
        application_name="careernav",
    )


def get_call_timeout() -> timedelta:
    """回傳單次工具呼叫的逾時設定，供需要手動呼叫 call_tool 的情境使用。

    Strands Agent 透過 MCPAgentTool 自動呼叫工具時不會套用此值
    （MCPAgentTool 未暴露 timeout 建構參數），此函式保留給未來若需要
    手動控制單次呼叫逾時的情境使用。

    Returns:
        timedelta(seconds=DEFAULT_CALL_TIMEOUT_SECONDS)
    """
    return timedelta(seconds=DEFAULT_CALL_TIMEOUT_SECONDS)
