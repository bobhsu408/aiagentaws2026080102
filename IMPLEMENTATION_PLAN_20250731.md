# 職涯導航家（CareerNav）— 完整實作計畫

> 建立日期：2026-07-31
> 目標：在比賽日（8/1-8/2）前完成可 demo 的端到端系統
> AWS Region: `us-west-2`
> Model: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

---

## 總覽

本計畫將既有的文件規劃、資料研究、scraper 模組，整合為一個可部署的 Strands Agent 系統。

```
目標架構：
┌────────────────────────────────────────────────────────┐
│  瀏覽器 (S3 Static / Local)                              │
│  └── HTTP POST                                         │
│       ▼                                                │
│  Lambda: careernav-proxy                               │
│  └── boto3 invoke_agent (SigV4)                        │
│       ▼                                                │
│  Amazon Bedrock AgentCore Runtime                      │
│  ├── Strands Agent (Claude Sonnet 4.5)                 │
│  ├── 6 Career Tools                                    │
│  ├── MCP Client → Exa AI                              │
│  └── AgentCore Memory                                  │
└────────────────────────────────────────────────────────┘
```

---

## Task 清單

### Task 1：專案基礎設施設置

**目標**：建立完整的專案骨架，讓後續 Task 有明確的檔案位置可以開發。

**產出**：
- `agent/` — Agent 程式碼目錄
  - `agent/main.py` — Agent 進入點（骨架）
  - `agent/tools/` — 六步驟工具目錄
  - `agent/data/` — 靜態資料目錄
  - `agent/pyproject.toml` — Python 依賴宣告
- `infra/` — CDK 基礎設施
  - `infra/package.json` — CDK 依賴
  - `infra/tsconfig.json` — TypeScript 設定
  - `infra/lib/stack.ts` — AgentCore CDK Stack
  - `infra/bin/app.ts` — CDK App 進入點
- `agentcore.json` — AgentCore 專案宣告
- `.env.example` — 環境變數範本
- `.gitignore` — 更新排除規則
- `scripts/` — 部署與工具腳本目錄

**驗收**：`cd infra && npm install && npx cdk synth` 能產出 CloudFormation template。

---

### Task 2：實作 resources_v2.json（新版補助資料）

**目標**：按 `RESOURCES_SCHEMA_PROPOSAL.md` 建立正確的結構化補助資料。

**產出**：
- `agent/data/resources.json` — 15~20 筆正確補助資料
- `agent/data/constants.json` — 全局常數（最低工資等）

**驗收**：
- 每筆有 `law_references`、`recipient`、`last_verified`
- 金額可追溯到法條
- 無 `CURRENT_DATA_ISSUES.md` 中列出的錯誤

---

### Task 3：實作六步驟 Career Tools

**目標**：完成 Agent 的核心工具函式。

**產出**：
- `agent/tools/career_tools.py` — 六個 `@tool` 裝飾的函式
- `agent/tools/__init__.py` — 匯出

**六步驟**：
1. `analyze_profile` — 解析自然語言描述為結構化 profile
2. `match_resources` — 比對 profile vs resources.json 的 eligibility
3. `calculate_benefit` — 根據 profile + 匹配結果計算金額
4. `generate_roadmap` — 產出 1~6 個月行動計畫
5. `get_checklist` — 回傳應備文件清單
6. `send_notification` — 模擬通知（demo 用）

**驗收**：每個 tool 可獨立呼叫並回傳合理結果。

---

### Task 4：Agent 主程式與 System Prompt

**目標**：完成 Agent 的編排邏輯與人設。

**產出**：
- `agent/main.py` — 完整的 Agent 進入點
- `agent/prompts/system_prompt.py` — System Prompt

**驗收**：本地 `python -m agent.main` 可啟動 Agent 並完成對話。

---

### Task 5：MCP Client 整合（Exa AI）

**目標**：接入 Exa AI 即時搜尋，加 timeout + fallback。

**產出**：
- `agent/mcp/client.py` — MCP Client 封裝
- `agent/mcp/__init__.py`

**驗收**：Agent 可即時搜尋並在搜尋失敗時 graceful degradation。

---

### Task 6：CDK 基礎設施完善 + AgentCore 部署

**目標**：用 CDK 部署 AgentCore Runtime。

**產出**：
- `infra/lib/stack.ts` — 完整的 IAM Role + AgentCore 資源
- 部署腳本 `scripts/deploy.sh`

**驗收**：`agentcore deploy` 成功，`agentcore invoke` 可得回覆。

---

### Task 7：Lambda Proxy + 前端接入

**目標**：讓瀏覽器可以透過 HTTP 跟 Agent 對話。

**產出**：
- `lambda/proxy.py` — Lambda handler
- `lambda/requirements.txt`
- `scripts/deploy_lambda.sh`
- `frontend/index.html` — 聊天頁面

**驗收**：瀏覽器打字 → 收到 Agent 完整回覆。

---

### Task 8：端到端測試 + 修正

**目標**：三個測試案例通過完整六步驟。

**測試案例**：
1. 小明 35歲餐廳主管被裁員
2. 55歲工廠女工育有幼兒
3. 28歲身障者想轉職

**驗收**：金額正確、有法規引用、無併領矛盾。

---

### Task 9：Demo 準備 + 簡報素材

**目標**：比賽現場可流暢 demo。

**產出**：
- Demo 腳本（3 分鐘版）
- 備用截圖（網路不穩時用）
- 技術架構圖（簡報用）

---

## 執行順序與依賴

```
Task 1 (基礎設施) ──┐
                    ├→ Task 3 (Tools) ──┐
Task 2 (資料) ──────┘                   ├→ Task 4 (Agent) → Task 5 (MCP)
                                        │
                                        └→ Task 6 (部署) → Task 7 (前端) → Task 8 (測試)
                                                                                    │
                                                                                    └→ Task 9 (Demo)
```

---

## 時間預估

| Task | 預估時間 | 累計 |
|------|----------|------|
| Task 1 | 1 hr | 1 hr |
| Task 2 | 3 hr | 4 hr |
| Task 3 | 3 hr | 7 hr |
| Task 4 | 1.5 hr | 8.5 hr |
| Task 5 | 1 hr | 9.5 hr |
| Task 6 | 2 hr | 11.5 hr |
| Task 7 | 2 hr | 13.5 hr |
| Task 8 | 1.5 hr | 15 hr |
| Task 9 | 1 hr | 16 hr |

**總計約 16 小時**。比賽可用時間約 16 小時（8/1 09:00-18:00 + 8/2 09:00-14:00，扣除提案交流和休息）。

---

## 關鍵決策

| 決策 | 理由 |
|------|------|
| Agent 程式碼放 `agent/` 而非 `app/career_navigator/` | 新起專案結構更乾淨，舊架構文件參考用 |
| CDK 放 `infra/` | 標準 monorepo 結構 |
| 資料靜態打包 | 比賽帳號無 DynamoDB，靜態 JSON 零依賴 |
| Lambda proxy 方案優先 | 最簡單的前端接入方式 |
| 使用 `strands-agents` SDK | 比賽指定技術棧 |

---

## 風險與備案

| 風險 | 備案 |
|------|------|
| 比賽帳號 Lambda 權限不足 | 改用 Cognito Identity Pool + 前端直連 AgentCore |
| AgentCore 部署失敗 | 本地跑 Agent + ngrok 暴露 |
| 時間不夠做完 | 優先確保 Task 1-4-6-7 可 demo，資料用精簡版 |
| Exa MCP 掛掉 | graceful degradation，跳過即時搜尋 |

---

## 參考文件

- `docs/HANDOFF.md` — 專案全貌
- `docs/DATA_STRATEGY.md` — 資料三層策略
- `docs/RESOURCES_SCHEMA_PROPOSAL.md` — 新版 schema 設計
- `docs/CURRENT_DATA_ISSUES.md` — 現有資料錯誤
- `docs/TODO_NEXT_SESSIONS.md` — 原待辦清單
- `scraper/` — 法規擷取模組（可直接使用）
