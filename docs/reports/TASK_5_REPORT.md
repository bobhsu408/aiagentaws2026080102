# Task 5 完成報告 — MCP Client 整合（Exa AI）

> 完成日期：2026-08-01
> 對應計畫：`docs/IMPLEMENTATION_PLAN_20250731.md` Task 5
> 前置：Task 3（六步驟 Career Tools）、Task 4（Agent 主程式，隨 Task 3 完成）

---

## 一、目標

接入 Exa AI 的即時搜尋能力（第 3 層資料來源，見 `docs/DATA_STRATEGY.md`），
讓 Agent 能在對話中補充「會隨時間變動」的動態資訊（開課梯次、職缺趨勢），
並確保連線失敗或逾時時不會拖垮整個 Agent（timeout + graceful degradation）。

---

## 二、關鍵決策（與使用者確認後定案）

| 編號 | 議題 | 決策 |
|------|------|------|
| D1 | 套件命名 | **不用 `mcp/` 而用 `exa_mcp/`**。`main.py` 會把 `app/careernav/` insert 進 `sys.path` 最前面，若資料夾叫 `mcp` 會蓋掉 PyPI 上 strands 依賴的 `mcp`（Model Context Protocol SDK）本身，導致 `ModuleNotFoundError: No module named 'mcp.client'`（已用 `/tmp` 沙盒實測重現）。這點偏離了 `docs/HANDOFF.md` 原先建議的 `app/careernav/mcp/` 路徑，已向使用者說明原因並取得同意。 |
| D2 | 開放哪些 Exa 工具 | 只開預設兩個：`web_search_exa`（網頁搜尋）、`web_fetch_exa`（抓取指定網址全文）。不開 `web_search_advanced_exa`（進階篩選）與 `agent_run`（Exa Agent，需額外認證且成本較高），demo 情境不需要。 |
| D3 | timeout 秒數 | 連線逾時（`startup_timeout`）10 秒、單次查詢逾時 15 秒。使用者確認可接受，前端後續（Task 7）會加載入動畫緩解等待感。 |
| D4 | 失敗處理策略 | 用 Strands `MCPClient(continue_on_error=True)`：連不上時 `load_tools()` 回傳空清單而非拋例外，Agent 仍能用其餘六個 Career Tools 正常運作，只是少了即時搜尋。不用自己刻 retry/fallback 邏輯，直接用 SDK 內建機制。 |
| D5 | 認證方式 | Exa 官方端點預設 keyless（有速率限制）。若 `.env` 提供 `EXA_API_KEY`，依官方文件唯一支援的方式以 URL query string 帶入（無 Authorization header 替代方案，已知風險見下方第六節）。 |

---

## 三、產出檔案

```
app/careernav/
├── main.py                          # 新增：import exa_mcp.client，
│                                     #   Agent(tools=[*TOOL_REGISTRY, _exa_mcp_client])
│                                     #   System Prompt 加「即時搜尋工具」使用規範
├── exa_mcp/                         # 新增套件（非 mcp/，見決策 D1）
│   ├── __init__.py                  # 說明命名理由，刻意不 import client.py
│   └── client.py                    # get_exa_mcp_client() 建立 MCPClient
├── pytest.ini                       # 新增：註冊 @pytest.mark.network 標記
└── tests/
    └── test_exa_mcp_client.py       # 新增：5 個測試（URL 組裝 3 個、
                                      #   graceful degradation 1 個、
                                      #   真實連線驗證 1 個）

.env.example                          # 更新 EXA_API_KEY 註解，說明傳遞方式與風險
```

---

## 四、設計重點

### 4.1 為何不叫 `mcp/`

`app/careernav/main.py` 開頭有：
```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```
這會讓 `app/careernav/` 本身變成 import 路徑最優先的位置。若在此目錄下建立
`mcp/` 資料夾，`import mcp`（或 `from mcp.client... import ...`）會優先解析到
我們自己的空殼套件，蓋掉 PyPI 上 `mcp`（Model Context Protocol SDK，strands
的直接依賴）。已用 `/tmp` 建立最小重現案例驗證，結果為
`ModuleNotFoundError: No module named 'mcp.client'`。改名為 `exa_mcp/` 後
完全避開此衝突，且與 Task 3 沿用 `strands import tool` 頂層匯入問題屬同一類
「import 路徑陷阱」，值得記錄避免未來重踩。

### 4.2 `get_exa_mcp_client()` 的組裝邏輯

```python
def get_exa_mcp_client(startup_timeout=10, url_override=None) -> MCPClient:
    url = url_override or _build_exa_mcp_url()
    def _transport():
        from mcp.client.streamable_http import streamablehttp_client
        return streamablehttp_client(url=url)
    return MCPClient(
        _transport,
        startup_timeout=startup_timeout,
        continue_on_error=True,
        application_name="careernav",
    )
```

- `_build_exa_mcp_url()` 組出 `https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa`，
  若 `EXA_API_KEY` 存在則附加 `&exaApiKey=...`。
- `_transport` 內才 `import mcp.client.streamable_http`，避免在無網路/無
  mcp 套件的環境（如僅測 `logic.py` 的單元測試）匯入整個模組時失敗。
- 回傳的 `MCPClient` 是 Strands 的 `ToolProvider`，`main.py` 直接把它放進
  `Agent(tools=[*TOOL_REGISTRY, _exa_mcp_client])`，Strands 會在 Agent
  建構時自動呼叫 `load_tools()` 並註冊工具，不需要手寫 list_tools 邏輯。

### 4.3 System Prompt 補充

加入「即時搜尋工具」段落，明確界定使用範圍：只用於動態資訊（開課梯次、
職缺趨勢），不得用於補助金額/資格/法規（那些以 `calculate_benefit` /
`match_resources` 的結構化資料為準）；並指示搜尋失敗時直接跳過、不要讓
使用者等待或反覆重試。

---

## 五、驗證結果

### 5.1 單元測試

```
$ ~/careernav_venv/bin/python -m pytest tests/ -v
tests/test_career_tools.py .............. (15 個，Task 3 既有，全數通過)
tests/test_exa_mcp_client.py
  test_build_url_without_api_key            PASSED
  test_build_url_with_api_key               PASSED
  test_build_url_only_enables_two_default_tools PASSED
  test_connection_failure_degrades_gracefully   PASSED
  test_real_exa_connection_lists_default_tools  PASSED
======================== 20 passed in 1.81s ========================
```

- `test_connection_failure_degrades_gracefully`：故意連往 `127.0.0.1:1`
  （保留埠、無服務），驗證 `load_tools()` 回傳 `[]` 而非拋例外，且
  `client.connection_failed is True`。證明 timeout + graceful degradation
  確實生效。
- `test_real_exa_connection_lists_default_tools`：實際連上
  `https://mcp.exa.ai/mcp`，確認回傳工具含 `web_search_exa` 與
  `web_fetch_exa`（本次驗證環境有網路，非跳過狀態）。

### 5.2 端到端整合驗證（Agent 實際註冊工具）

```python
agent = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    system_prompt="test",
    tools=[*TOOL_REGISTRY, get_exa_mcp_client()],
)
# agent.tool_names ==
# ['analyze_profile', 'calculate_benefit', 'generate_roadmap', 'get_checklist',
#  'match_resources', 'send_notification', 'web_fetch_exa', 'web_search_exa']
```

確認 `main.py` 實際會用的組裝方式（六步驟工具 + Exa MCP client 一起放入
`Agent(tools=[...])`）能成功產出 8 個工具，六步驟工具與 Exa 搜尋工具皆正確
註冊。

### 5.3 語法檢查

```
$ ~/careernav_venv/bin/python -m py_compile main.py exa_mcp/client.py exa_mcp/__init__.py
SYNTAX OK
```

---

## 六、已知限制與風險

1. **Exa API key 傳遞方式**：官方文件（`exa-labs/exa-mcp-server`）目前唯一
   支援的方式是 URL query string（`?exaApiKey=...`），沒有 Authorization
   header 替代方案。社群已有 GitHub issue（#334）反映此安全性顧慮，但這是
   Exa 服務端的限制，非本專案程式碼可規避。`.env` 中的 `EXA_API_KEY` 已由
   `.gitignore` 排除，不會進版本控制；比賽 demo 若填入金鑰，注意勿在任何
   log／截圖／分享的 URL 中外洩。完整風險說明與因應措施見
   `docs/EXA_MCP_API_KEY_SECURITY.md`。
2. **本次 demo 未填 `EXA_API_KEY`**：確認 `.env` 中該欄位為空，Exa 端點以
   keyless 模式運作，有速率限制。若 demo 現場密集測試觸發 429，Agent 會依
   System Prompt 指示優雅跳過搜尋，不影響其餘六步驟。
3. **Runtime 尚未重新部署**：本 Task 只改 `app/careernav/` 原始碼，尚未執行
   `agentcore deploy` 重新打包上線（屬 Task 6 範圍）。線上 Runtime 目前仍是
   Task 3 之前的舊骨架。
4. **UI 載入動畫**：使用者提出希望在等待搜尋結果時，前端顯示「查詢中」的
   小動畫，避免使用者誤以為卡住。此為 Task 7（前端接入）範疇，本 Task 僅
   記錄需求，尚未實作。
5. **`read_timeout_seconds`（單次查詢逾時）未實際套用於 Agent 自動呼叫路徑**：
   Strands 的 `MCPAgentTool.stream()` 呼叫 `call_tool_async` 時未暴露可由
   `MCPClient` 建構參數設定單次呼叫逾時的介面；`get_call_timeout()` 保留
   供未來手動呼叫情境使用，但目前 Agent 透過工具自動呼叫時只受
   `startup_timeout`（連線層）保護。若之後發現單次搜尋卡住不回應，需再次
   確認 Strands SDK 是否有更新的 API 可設定 per-call timeout。

---

## 七、下一步

依 `docs/IMPLEMENTATION_PLAN_20250731.md`，下一個建議 Task 是 **Task 6：
CDK 基礎設施完善 + AgentCore 部署**（重新打包含 Task 3～5 全部程式碼並
`agentcore deploy`），或視使用者優先序調整。
