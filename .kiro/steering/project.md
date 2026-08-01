# 職涯導航家（CareerNav）— 專案引導文件

## 專案概述

參加 **2026 雲湧智生：臺灣生成式 AI 應用黑客松**（TIARA 出題）。

核心產品：一站式 AI 對話 Agent，幫助失業/轉職者快速了解自身可申請的政府補助、產出完整轉職行動計畫。

## 技術架構

```
瀏覽器 → Lambda (proxy) → Amazon Bedrock AgentCore → Strands Agent (Claude Sonnet 4.5)
                                                      ├── 6 Career Tools
                                                      ├── MCP Client → Exa AI（即時搜尋）
                                                      └── AgentCore Memory
```

## 技術棧

| 層級 | 技術 |
|------|------|
| Agent 框架 | `strands-agents` (Python) |
| LLM | Claude Sonnet 4.5 via Bedrock |
| 託管 | Amazon Bedrock AgentCore (Python 3.14) |
| 基礎設施 | AWS CDK (`@aws/agentcore-cdk`, TypeScript) |
| 即時搜尋 | Exa AI via MCP |
| 部署 | `agentcore deploy` CLI |
| 資料擷取 | Python scraper 模組（Selenium + 法規 API） |

## 六步驟 Pipeline

1. `analyze_profile` — 解析使用者背景
2. `match_resources` — 匹配符合資格的補助方案
3. `calculate_benefit` — 試算金額
4. `generate_roadmap` — 產出時間軸行動計畫
5. `get_checklist` — 應備文件清單
6. `send_notification` — 通知（demo 模擬）

## 資料來源三層架構

- **第 1 層（法規）**：全國法規資料庫 API，免金鑰，自動擷取
- **第 2 層（行政計畫）**：手動整理，標註 source_url + last_verified
- **第 3 層（即時）**：Exa AI MCP，Agent runtime 即時搜尋

## 檔案結構重點

- `scraper/` — 資料擷取模組（台灣就業通 + 法規 API）
- `data_pipeline/` — 舊版擷取腳本
- `docs/` — 專案文件（策略、交接、待辦等）
- 主要 Agent 程式碼不在此 repo（在 AgentCore 部署包中）

## 開發規範

- Python 程式碼使用 type hints
- 爬蟲模組遵循 `BaseScraper` 介面，新來源建子資料夾 + 註冊到 `__init__.py`
- 資料檔案輸出為 JSON 格式
- 法規相關資料必須附 `law_references`（條號 + URL）
- 補助資料標明 `recipient`（勞工/雇主）避免混淆

## 重要限制

- 比賽帳號為 AWS Workshop Studio 沙盒，缺 DynamoDB / API Gateway / SES / SNS
- 正式比賽當天會發新帳號，權限未知
- 台灣就業通網站為 Big5 編碼、結構不穩定，爬蟲需 Selenium + Chrome
- `resources.json` 為靜態打包，不依賴即時抓取

## 參考文件

- #[[file:docs/DATA_STRATEGY.md]] — 資料從哪來、怎麼用
- #[[file:docs/HANDOFF.md]] — 專案交接全貌
- #[[file:docs/TODO_NEXT_SESSIONS.md]] — 待辦事項優先序
- #[[file:scraper/README.md]] — 擷取模組使用說明
