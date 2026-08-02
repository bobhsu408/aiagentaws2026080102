"""Exa MCP 套件 — 第 3 層即時搜尋整合

- client.py：建立連往 Exa AI MCP 伺服器（https://mcp.exa.ai/mcp）的
  MCPClient，供 main.py 註冊進 Agent，讓 Agent 能即時搜尋補充資訊。

命名說明：此套件刻意不叫 `mcp`，因為 `app/careernav/main.py` 會將本目錄
insert 進 sys.path 最前面，若資料夾叫 `mcp` 會蓋掉 PyPI 上 strands 依賴
的 `mcp`（Model Context Protocol SDK）套件本身，導致
`ModuleNotFoundError: No module named 'mcp.client'`（已實測驗證）。

注意：本 __init__ 刻意不 import client.py，避免在沒有 strands / mcp 套件的
環境（如單元測試）匯入整個套件時失敗。需要時請直接
`from exa_mcp.client import get_exa_mcp_client`。
"""
