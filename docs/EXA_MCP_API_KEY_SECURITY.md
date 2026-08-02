# Exa AI MCP：API Key 傳遞方式與已知安全性風險

> 目的：記錄 Exa AI 遠端 MCP 端點的官方認證方式、社群提出的安全性顧慮，以及本專案的因應措施。可直接作為黑客松報告中「已知限制／風險評估」段落的素材。

## 一、官方做法

Exa AI 官方託管的遠端 MCP 伺服器（`https://mcp.exa.ai/mcp`）**不支援 Authorization header 傳遞金鑰**。目前官方文件唯一支援的認證方式是把 API key 接在 URL 的 query string 上：

```
https://mcp.exa.ai/mcp?exaApiKey=YOUR_KEY&tools=web_search_exa,web_fetch_exa
```

`tools` 參數用來指定要啟用哪些工具（預設啟用 `web_search_exa`、`web_fetch_exa`），`exaApiKey` 則是選填。

### Keyless 模式

即使不帶 `exaApiKey`，端點也能直接使用（免費方案，有速率限制；命中 429 時官方建議附上自己的 API key 以提高額度）。本專案 demo 情境下，keyless 模式的速率限制通常已足夠，帶 key 只是為了提高穩定度。

來源：[Exa 官方文件 - Web Search MCP](https://docs.exa.ai/examples/exa-mcp)

## 二、社群提出的安全性顧慮

2026 年初，有人在 Exa MCP Server 的 GitHub repo 提出 issue，指出官方 README 範例把 API key 直接寫在 URL query string 裡並不安全。理由是 query string 型態的機密資訊很容易經由 shell 歷史紀錄、client 端日誌、proxy 日誌、瀏覽器歷史、螢幕截圖、支援案件附件等管道外洩；對 MCP 設定檔而言，這類 URL 也常被整份複製貼上到別的工具或明文設定檔中留存。

該 issue 建議官方改採以下任一方式：

- Authorization header
- MCP client 的 secret／環境變數欄位
- 本機 stdio 設定搭配 `EXA_API_KEY` 環境變數
- 或至少在文件中加註警告：query string 認證雖方便，但在共用或會被記錄的環境中應避免使用

來源：[exa-labs/exa-mcp-server, Issue #334 — "Remote MCP docs show API key in URL query string"](https://github.com/exa-labs/exa-mcp-server/issues/334)（內容經改寫摘要，非逐字引用）

截至本文件撰寫時（2026-08-01），Exa 官方尚未在遠端 MCP 端點提供 header 型認證的替代方案；query string 仍是唯一支援的遠端傳遞方式。

## 三、本專案的因應措施

由於 Exa 官方端點本身的限制無法從客戶端規避，本專案採取以下方式降低風險：

1. **不寫入程式碼、不進版本控制**：`EXA_API_KEY` 只存在於本機 `.env`（已列入 `.gitignore`），程式碼中僅在執行時透過環境變數讀取。`.env.example` 只保留欄位名稱，不含實際金鑰值。
2. **執行時才組出完整 URL**：`app/careernav/exa_mcp/client.py` 在建立 MCPClient 時才動態組出含 `exaApiKey` 的 URL，金鑰不會出現在原始碼、log 訊息或其他持久化檔案中。
3. **Keyless 為預設容錯路徑**：`EXA_API_KEY` 未設定時，直接用 keyless 模式呼叫（僅受官方免費方案速率限制），不會因為缺金鑰而讓 Agent 掛掉。
4. **Graceful degradation**：MCPClient 以 `continue_on_error=True` 建立，Exa 端點連不上時 Agent 仍可用其餘六個 Career Tools 正常運作，只是少了即時搜尋能力。
5. **風險留存記錄**：程式碼（`client.py` docstring）與本文件皆註記此為 Exa 服務端限制，非本專案可規避的程式碼問題，方便未來交接或稽核時追溯。

## 四、報告可用的一句話總結

> 我們確認了 Exa 官方文件的做法：遠端 MCP 端點傳遞 API key 的方式是接在 URL query string 上，沒有 API key 也能用（keyless，有速率限制）。社群在 GitHub 上已提出這種傳遞方式不夠安全，但這是 Exa 官方目前唯一支援的方式，沒有 header 替代方案。我們的因應方式是用環境變數控制金鑰、不寫入程式碼或版本控制，並在文件中註記此已知風險。

## 參考來源

- [Exa 官方文件 - Web Search MCP](https://docs.exa.ai/examples/exa-mcp)
- [exa-labs/exa-mcp-server Issue #334](https://github.com/exa-labs/exa-mcp-server/issues/334)
- 專案內對應實作：`app/careernav/exa_mcp/client.py`
- 相關資料策略：`docs/DATA_STRATEGY.md`、`docs/DATA_SOURCES_VERIFIED.md`
