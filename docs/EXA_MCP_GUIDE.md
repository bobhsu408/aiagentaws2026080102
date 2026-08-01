# Exa AI MCP 工具說明文件

> 用途：讓不熟悉 MCP／Agent 技術背景的人（例如資管系大學生、評審、隊友）也能看懂 Exa AI 這個工具在本專案扮演的角色。每個小節都分成「專業說明」與「白話講」兩段，專業說明給技術審查用，白話講給口頭報告或新成員上手用。

## 一、這個工具是什麼

**專業說明**

Exa AI MCP 是 Exa 公司官方託管的一個遠端 MCP（Model Context Protocol）伺服器，端點為 `https://mcp.exa.ai/mcp`。它把 Exa 的網路搜尋 API 包裝成標準化的 MCP 工具介面，讓任何支援 MCP 的 Agent 框架（本專案用 `strands-agents`）都能直接掛載它，取得即時網路搜尋與網頁擷取能力，不需要自己寫爬蟲或串接搜尋 API。

**白話講**

想像 Agent 是一個很聰明但「知識停在訓練那一刻」的助理，它不知道今天早上發布的新聞、最新的職缺公告、剛開課的課程資訊。Exa MCP 就像是幫這個助理裝一個「即時 Google 搜尋外掛」，它問一個問題，外掛就去網路上查最新結果，把摘要交給助理繼續回答使用者。

## 二、MCP 是什麼、為什麼不直接用 API

**專業說明**

MCP（Model Context Protocol）是 Anthropic 提出的開放協定，定義 LLM Agent 與外部工具／資料源之間統一的溝通格式（工具清單、呼叫參數、回傳結果的 schema 都標準化）。好處是 Agent 框架只要實作一次 MCP client，就能接上任何遵循 MCP 的伺服器，不用為每個第三方 API 各寫一套整合邏輯。本專案的 Strands Agent 透過 `strands.tools.mcp.mcp_client.MCPClient` 建立連線，Exa 的搜尋工具會自動出現在 Agent 可呼叫的工具清單裡，跟其他六個 Career Tools 平等對待。

**白話講**

沒有 MCP 之前，如果你想讓 AI 助理連上「搜尋工具」「資料庫工具」「行事曆工具」，每一個都要自己寫一套「怎麼問、怎麼收資料」的規則，很麻煩。MCP 就是大家講好的一套「共同語言」，工具只要照這個語言講話，AI 助理就聽得懂，不用客製化。Exa 選擇用 MCP 對外開放，我們就直接照這個語言接上去，省掉自己寫搜尋串接的功夫。

## 三、這個工具能做什麼（提供哪些能力）

**專業說明**

Exa MCP 端點預設啟用兩個工具，本專案在建立連線時透過 `tools` query 參數明確只開放這兩個（`app/careernav/exa_mcp/client.py` 的 `_EXA_ENABLED_TOOLS`）：

| 工具 | 功能 |
|------|------|
| `web_search_exa` | 輸入查詢字串，回傳相關網頁的乾淨摘要內容 |
| `web_fetch_exa` | 輸入一個或多個網址，回傳該網頁完整內容轉成的 markdown 文字 |

官方端點還有進階工具（`web_search_advanced_exa` 可設定分類/網域/日期篩選、`agent_run` 可跑多步驟研究），本專案 demo 情境不需要，故未開啟，可降低不必要的呼叫成本與複雜度。

**白話講**

`web_search_exa` 就是「幫我查一下」——你給它關鍵字，它給你幾筆相關網頁的重點摘要，類似丟關鍵字進搜尋引擎、然後把搜尋結果頁的摘要整理好給你。`web_fetch_exa` 是「幫我讀這個網址」——你給它一個連結，它把整個網頁的內容轉成乾淨的文字給你，不用自己開瀏覽器複製貼上。我們只開這兩個基本功能，因為 demo 情境只需要「查資料」跟「讀網頁」，進階的「跑一整套自動研究」用不到，開了反而增加出錯與被扣分的風險。

## 四、在本專案的角色（資料來源第三層）

**專業說明**

本專案的資料來源分三層（詳見 `docs/DATA_STRATEGY.md`）：第一層是全國法規資料庫 API（權威、穩定、免金鑰）；第二層是手動整理的行政計畫資料（附 `source_url`／`last_verified`）；第三層才是 Exa MCP，用於補充「即時、會變動、法規查不到」的資訊，例如最新職缺趨勢、課程開課梯次。`generate_roadmap` 工具的輸出已預留 `course_hint`／`hint.keywords` 欄位，供 Agent 在對話中決定是否呼叫 Exa 搜尋補充。Exa 的搜尋結果**不能**作為金額或資格認定的依據，只能當補充參考，這點在 system prompt 與資料策略文件中都有明確規範。

**白話講**

把整個系統想成三層資料架構：第一層是「法律條文」，最權威但更新慢；第二層是「政府公告的計畫」，我們人工幫忙整理好、附上來源連結；第三層是「即時搜尋」，用來補那些法規查不到、需要「現在」資訊的東西，比如「這個月哪裡有職訓班在招生」。Exa 就是負責第三層。重要原則是：Exa 查到的東西只能當「參考建議」,絕對不能拿來當「你可以領多少錢」的依據，因為網路搜尋結果不保證準確，金額還是要看法規跟官方公告。

## 五、認證方式與已知風險

**專業說明**

Exa 官方端點支援 keyless 呼叫（免金鑰，有速率限制），也支援以 URL query string 帶入 `exaApiKey` 提高額度。官方文件目前**沒有** Authorization header 的替代方案，社群已在 GitHub（[exa-labs/exa-mcp-server Issue #334](https://github.com/exa-labs/exa-mcp-server/issues/334)）提出此設計有洩漏風險。本專案因應方式：`EXA_API_KEY` 只存在本機 `.env`（已排除於版本控制），程式碼執行時才動態組出含金鑰的 URL，未寫死在原始碼或 log 中；未設定金鑰時自動降級為 keyless 模式。完整風險評估見 `docs/EXA_MCP_API_KEY_SECURITY.md`。

**白話講**

要不要放 API key 是選擇題：不放也能用（免費方案有次數限制），放了額度比較高。麻煩的是,Exa 目前「唯一」支援放金鑰的方式是直接寫在網址後面（像 `?exaApiKey=xxx`），這種寫法有個已知缺點——網址常常會被記錄下來（瀏覽紀錄、log、截圖),金鑰有洩漏風險。這不是我們程式碼寫得不好,是 Exa 官方目前就只提供這一種方式。我們的做法是把金鑰放在 `.env`（不會被 commit 進 Git),程式執行時才組出網址,盡量降低外流機會,並且在文件裡誠實記錄這個限制,這在報告時是可以主動講的加分項（顯示有做風險評估）。

## 六、本專案怎麼串接（程式碼概覽）

**專業說明**

實作位於 `app/careernav/exa_mcp/client.py`，核心函式 `get_exa_mcp_client()` 建立一個 `MCPClient` 實例並注入到 `main.py` 的 Agent 工具清單。關鍵設計：

- **connection timeout**：`startup_timeout`（預設 10 秒）限制建立連線最長等待時間，避免 Exa 服務異常時卡住整個 Agent 初始化。
- **graceful degradation**：以 `continue_on_error=True` 建立 client，連線失敗時 Strands 會讓這個 provider 回傳空工具清單,而不是丟例外中斷 Agent。也就是說即使 Exa 掛掉,其餘六個 Career Tools（`analyze_profile`、`match_resources`、`calculate_benefit`、`generate_roadmap`、`get_checklist`、`send_notification`）仍能正常運作。
- **延遲載入 transport**：`streamablehttp_client` 只在真正建立連線時才 import,避免無網路的單元測試環境因為缺少 `httpx`/`anyio` 而載入失敗。

**白話講**

程式碼做了三件保護措施,讓 Exa 這個外部依賴不會拖垮整個系統：

1. 設定「連線最多等 10 秒」,不會因為 Exa 網站很慢就讓使用者在對話視窗前空等。
2. 如果連不上 Exa,系統會「優雅地」跳過這個工具,繼續用其他六個工具正常回答,而不是整個當機給使用者看錯誤訊息。這種設計叫「graceful degradation（優雅降級）」,是後端系統常見的容錯手法,概念類似「某個外部服務掛了,主功能還是要能跑」。
3. 只有在真的要連線時才載入相關套件,避免跑單元測試時因為沒有網路環境而失敗——測試不需要真的連上 Exa,只要驗證程式邏輯正確就好。

## 七、目前限制（誠實揭露）

**專業說明**

- Exa 搜尋結果品質不穩定，可能回傳不相關內容，不適合作為金額/資格判斷的唯一依據。
- `web_fetch_exa`／`web_search_exa` 的呼叫本身沒有獨立的單次逾時封裝在 Strands 的 `MCPAgentTool` 自動呼叫路徑上（`get_call_timeout()` 目前僅保留給未來手動呼叫情境使用）。
- 非官方權威來源，僅作補充資訊，不涵蓋在資料品質規範（`law_references`／`recipient`／`source_url`／`last_verified`）要求範圍內。

**白話講**

老實說這個工具有幾個還沒完美解決的地方：搜尋結果不一定準,AI 可能查到不相關的網頁；單次搜尋本身沒有额外的逾時保護（只有連線階段有設 10 秒上限）；而且它查到的東西不是官方權威資料,所以不會被當成補助金額的正式依據。這些都寫在文件裡,不是要藏起來,而是讓評審知道我們清楚知道這個工具的邊界在哪裡,這種「知道限制在哪」的態度本身就是加分。

## 參考來源

- [Exa 官方文件 - Web Search MCP](https://docs.exa.ai/examples/exa-mcp)
- [exa-labs/exa-mcp-server Issue #334](https://github.com/exa-labs/exa-mcp-server/issues/334)
- 專案內對應實作：`app/careernav/exa_mcp/client.py`
- 相關文件：`docs/EXA_MCP_API_KEY_SECURITY.md`、`docs/DATA_STRATEGY.md`、`docs/DATA_SOURCES_VERIFIED.md`
