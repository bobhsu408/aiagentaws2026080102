"""Exa MCP Client 測試

驗證 Task 5 的兩個核心驗收點：
1. graceful degradation：連不上時不拋例外，load_tools() 回傳空清單。
2. 正常連線時能列出 Exa 官方預設開啟的搜尋工具。

需要 strands-agents（含 mcp 依賴）才能執行，本機若無 strands 套件，
以 pytest.importorskip 跳過（與專案 tests/test_career_tools.py 的策略一致，
career_tools 測試靠 tools/__init__.py 刻意不 import strands 來達成同等效果）。
"""

import asyncio
import os
import sys

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import pytest

pytest.importorskip("strands", reason="需要 strands-agents 套件（含 mcp 依賴）才能測試 MCP Client")

from exa_mcp.client import (  # noqa: E402
    _build_exa_mcp_url,
    get_exa_mcp_client,
)


def test_build_url_without_api_key(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    url = _build_exa_mcp_url()
    assert url.startswith("https://mcp.exa.ai/mcp?tools=")
    assert "exaApiKey" not in url


def test_build_url_with_api_key(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "test-key-123")
    url = _build_exa_mcp_url()
    assert "exaApiKey=test-key-123" in url


def test_build_url_only_enables_two_default_tools(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    url = _build_exa_mcp_url()
    assert "web_search_exa" in url
    assert "web_fetch_exa" in url
    # 不應開啟進階搜尋或 Exa Agent（未經確認不啟用）
    assert "web_search_advanced_exa" not in url
    assert "agent_run" not in url
    assert "agent_tools" not in url


def test_connection_failure_degrades_gracefully():
    """連往一個不存在的位址，連線應在短時間內失敗，且 load_tools() 回傳空清單而非拋例外。"""
    # 127.0.0.1:1 通常是保留埠、不會有服務在聽，可快速觸發連線失敗（非等待逾時）。
    client = get_exa_mcp_client(
        startup_timeout=5,
        url_override="http://127.0.0.1:1/mcp",
    )
    tools = asyncio.run(client.load_tools())
    assert tools == []
    assert client.connection_failed is True


@pytest.mark.network
def test_real_exa_connection_lists_default_tools():
    """需要實際網路連線，驗證能連上 Exa 官方端點並列出預設工具。"""
    client = get_exa_mcp_client()
    tools = asyncio.run(client.load_tools())
    tool_names = {t.tool_name for t in tools}
    assert "web_search_exa" in tool_names
    assert "web_fetch_exa" in tool_names
    client.stop(None, None, None)
