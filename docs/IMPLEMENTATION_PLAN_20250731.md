# 職涯導航家（CareerNav）— 完整實作計畫

> 建立日期：2026-07-31
> 最後優化：2026-08-01（加入子代理平行執行策略）
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

## 執行模式圖例

每個 Task（或其子項）標記三種執行模式之一。判斷原則：**只有在「fan-out 收益 > 合併成本」時才平行**，不為平行而平行。

| 標記 | 模式 | 適用情境 | 誰來做 |
|------|------|----------|--------|
| 🧩 | **主代理獨作 (solo)** | 需內部一致性、跨檔語意判斷、緊耦合邏輯 | 主代理親自寫 |
| 🚀 | **可平行 (fan-out)** | 彼此獨立的查證、獨立產物、橫向研究 | 開子代理平行 |
| 🔒 | **純序列 (serial)** | 共用同一 AWS 環境、硬前後依賴 | 主代理依序執行 |

> **鐵則**：所有平行產物（子代理回傳的資料、程式碼片段）一律由**主代理彙整、校對、合併**，確保 schema 一致與 cross-reference 正確。子代理只負責「產出草稿 / 查證事實 / 獨立驗證」，不直接對共享檔案落最終版本。

---

## Task 清單

### Task 1：專案基礎設施設置　🧩 已完成

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

**執行模式**：🧩 主代理獨作（已於 commit `891e21a` 完成，報告 `docs/reports/TASK_1_REPORT.md`）。

---

### Task 2：實作 resources.json（新版補助資料）　🧩+🚀 混合

**目標**：按 `RESOURCES_SCHEMA_PROPOSAL.md` 建立正確的結構化補助資料。

**產出**：
- `agent/data/resources.json` — 15~20 筆正確補助資料
- `agent/data/constants.json` — 全局常數（最低工資等）

**驗收**：
- 每筆有 `law_references`、`recipient`、`last_verified`
- 金額可追溯到法條
- 無 `CURRENT_DATA_ISSUES.md` 中列出的錯誤

**執行模式拆分**：
- 🧩 **主代理獨作**：
  - 第 1 層法規類資料（失業給付、職訓生活津貼、提早就業獎助、眷屬加給、僱用獎助、創業貸款、異地就業三補助、育嬰留停、健保費補助等）— 已從 `output/laws_extracted.json` 核對 12 部法規原文，由主代理直接寫檔。
  - `constants.json` — 已完成（2026 基本工資月薪 29,500 / 時薪 196）。
  - **JSON 最終合併與 `concurrency_rules` 交互引用校對** — 因單一檔案需內部一致，必須由主代理落版。
- 🚀 **可平行（子代理 ×3）**：第 2 層行政計畫查證，彼此來源獨立：
  - 子代理 A：產業新尖兵試辦計畫（課程類型、補助上限、報名資格、`source_url`）
  - 子代理 B：微型創業鳳凰貸款（額度、利率、45 歲以上婦女/中高齡對象、與就保創業貸款的區別）
  - 子代理 C：婦女再就業 / 托育相關津貼查證（確認是否有中央法源，或標為地方方案）
- **合併協定**：子代理回傳「事實 + 來源 URL + 查證日期」，主代理轉為符合 schema 的 entry 並落檔。

---

### Task 3：實作六步驟 Career Tools　🧩+🚀 混合

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

**執行模式拆分**：
- 🧩 **主代理獨作（核心，緊耦合 schema）**：`match_resources` + `calculate_benefit`。這兩個直接讀 `benefit.base` / `conditional_tiers` / `surcharges` / `concurrency_rules`，錯一個欄位就全錯，必須主代理親寫並負責整份檔案的最終整合。
- 🚀 **可平行（子代理草稿）**：邏輯較獨立、彼此不衝突的工具可由子代理各自產出「純函式草稿 + 單元測試」，再由主代理併入同一檔案：
  - 子代理 A：`analyze_profile`（自然語言 → 結構化 profile 的解析規則）
  - 子代理 B：`generate_roadmap`（時間軸排程邏輯）
  - 子代理 C：`get_checklist` + `send_notification`（讀 `required_documents`、模擬通知）
- **禁止平行**：不要讓多個子代理同時「直接編輯」`career_tools.py`（同檔衝突）。子代理交付獨立函式與測試，合併由主代理序列進行。

---

### Task 4：Agent 主程式與 System Prompt　🧩 主代理獨作

**目標**：完成 Agent 的編排邏輯與人設。

**產出**：
- `agent/main.py` — 完整的 Agent 進入點
- `agent/prompts/system_prompt.py` — System Prompt

**驗收**：本地 `python -m agent.main` 可啟動 Agent 並完成對話。

**執行模式**：🧩 主代理獨作。Agent 編排、工具註冊順序、system prompt 的六步驟引導與人設是全域語意決策，平行拆解只會製造不一致。

---

### Task 5：MCP Client 整合（Exa AI）　🚀 可平行（提前啟動）

**目標**：接入 Exa AI 即時搜尋，加 timeout + fallback。

**產出**：
- `agent/mcp/client.py` — MCP Client 封裝
- `agent/mcp/__init__.py`

**驗收**：Agent 可即時搜尋並在搜尋失敗時 graceful degradation。

**執行模式**：🚀 可平行。此模組介面單純（輸入 query、輸出結果、失敗降級），與 Task 3 的資料工具解耦，**可在 Task 3 進行時由子代理先行開發**，最後由主代理在 Task 4 註冊進 Agent。

---

### Task 6：CDK 基礎設施完善 + AgentCore 部署　🔒 純序列（周邊 🚀 可平行）

**目標**：用 CDK 部署 AgentCore Runtime。

**產出**：
- `infra/lib/stack.ts` — 完整的 IAM Role + AgentCore 資源
- 部署腳本 `scripts/deploy.sh`

**驗收**：`agentcore deploy` 成功，`agentcore invoke` 可得回覆。

**執行模式拆分**：
- 🔒 **純序列**：實際 `agentcore deploy`、CDK `deploy`、Runtime 狀態驗證 — 共用同一 AWS 沙盒環境，狀態互斥，**絕不可平行**（同時部署會互相覆蓋 / 搶佔資源鎖）。
- 🚀 **可平行（前置準備）**：IAM policy 草擬、S3 bucket 設定、`stack.ts` 資源定義、部署腳本撰寫，可在 Task 3/4 進行時由子代理先備妥草稿。
- 備註：AgentCore Runtime 已於部署檢查點先行上線（見 `docs/reports/AGENTCORE_RUNTIME_DEPLOYMENT_REPORT.md`），本 Task 尚需完成 `infra/` 正式驗收與資料重新打包部署。

---

### Task 7：Lambda Proxy + 前端接入　🔒 純序列（前端 🚀 可平行）

**目標**：讓瀏覽器可以透過 HTTP 跟 Agent 對話。

**產出**：
- `lambda/proxy.py` — Lambda handler（須改用 AgentCore Runtime invocation API，非舊式 `invoke_agent`）
- `lambda/requirements.txt`
- `scripts/deploy_lambda.sh`
- `frontend/index.html` — 聊天頁面

**驗收**：瀏覽器打字 → 收到 Agent 完整回覆。

**執行模式拆分**：
- 🔒 **純序列**：Lambda 部署、串接 AgentCore Runtime、端到端連通測試 — 依賴 Task 6 的部署結果，且動到共享雲端資源。
- 🚀 **可平行**：`frontend/index.html` 的 UI/UX（聊天框、串流顯示、載入狀態）與 Lambda handler 邏輯彼此獨立，可由子代理平行開發，最後主代理串接。
- ⚠️ **安全提醒**：Function URL 目前設 `AuthType.NONE`（demo 用，無認證）。正式對外需評估加認證，落版前於報告標明此風險。

---

### Task 8：端到端測試 + 修正　🚀 可平行（3 案例並行）

**目標**：三個測試案例通過完整六步驟。

**測試案例**：
1. 小明 35歲餐廳主管被裁員
2. 55歲工廠女工育有幼兒
3. 28歲身障者想轉職

**驗收**：金額正確、有法規引用、無併領矛盾。

**執行模式**：🚀 可平行。三個測試案例彼此獨立，**開 3 個子代理各跑一個案例**，各自產出「invoke 輸入 → 實際回覆 → 金額/法規/併領正確性檢查表」。主代理彙整結果、判定是否需要回頭修 Task 2 資料或 Task 3 邏輯。

---

### Task 9：Demo 準備 + 簡報素材　🚀 可平行

**目標**：比賽現場可流暢 demo。

**產出**：
- Demo 腳本（3 分鐘版）
- 備用截圖（網路不穩時用）
- 技術架構圖（簡報用）

**執行模式**：🚀 可平行。三項產物彼此獨立，可開子代理分別產出（腳本文案 / 截圖流程 / 架構圖描述），主代理最後統一風格與定稿。

---

## 執行順序與平行波次（Wave）

在原依賴圖上疊加「可同時啟動」的波次。同一波內的工作可平行；跨波有依賴，須等前波關鍵產物完成。

```
Wave 0（已完成）
  Task 1 基礎設施 🧩

Wave 1（資料層，可開 3 子代理）
  Task 2-第1層法規資料 🧩（主代理）
  ├── 子代理A：產業新尖兵查證 🚀
  ├── 子代理B：微型創業鳳凰查證 🚀
  └── 子代理C：婦女托育津貼查證 🚀
  → 主代理合併落 resources.json

Wave 2（工具 + 提前備料，可開多子代理）
  Task 3-核心 match/calculate 🧩（主代理，依賴 Task 2 schema）
  ├── 子代理：analyze_profile / generate_roadmap / checklist 草稿 🚀
  ├── Task 5 MCP Client 🚀（提前開發，與 Task 3 解耦）
  └── Task 6 周邊 IAM/S3/腳本草稿 🚀（提前備妥）

Wave 3（編排，主代理獨作）
  Task 4 Agent 主程式 + System Prompt 🧩
  → 註冊 Task 3 工具 + Task 5 MCP

Wave 4（部署，純序列，不可平行）
  Task 6 正式部署 🔒 → Task 7 Lambda 串接 🔒
  ├── 平行：Task 7 前端 UI 🚀（與 Lambda 邏輯解耦）

Wave 5（驗證，可開 3 子代理）
  Task 8 三案例平行測試 🚀🚀🚀
  → 主代理彙整，必要時回修 Wave 1/2

Wave 6（收尾，可平行）
  Task 9 demo 腳本 / 截圖 / 架構圖 🚀
```

**關鍵序列瓶頸（無法平行、決定總工時下限）**：
`Task 2 schema 定案 → Task 3 核心邏輯 → Task 4 編排 → Task 6 部署 → Task 7 串接 → Task 8 驗證`

---

## 子代理（sub-agent）使用守則

**何時開子代理**
- 工作彼此獨立、產物不互相依賴（多筆資料查證、多個測試案例、多份 demo 素材）。
- 橫向研究 / 事實查證（官網現況、統計數據、權限探測）。
- 介面清楚、與主線解耦的獨立模組草稿（MCP Client、前端 UI、IAM 草案）。

**何時「不要」開子代理**
- 單一檔案需內部一致：`resources.json`（`concurrency_rules` 交互引用）、`career_tools.py`（同檔多函式）。→ 子代理可交草稿，但**落檔與合併只由主代理做**。
- 緊耦合 schema 的計算邏輯：`match_resources` / `calculate_benefit`。
- 全域語意決策：Agent 編排、system prompt。
- 共用單一 AWS 環境的部署動作：`agentcore deploy`、CDK deploy、Lambda 部署。→ 狀態互斥，平行會互相破壞。

**產物回收與合併協定**
1. 子代理交付「結構化事實 + 來源 URL + 查證日期」或「獨立函式 + 單元測試」，**不直接對共享檔案落最終版本**。
2. 主代理負責：schema 轉換、cross-reference 校對、風格統一、落檔。
3. 合併後由主代理跑一次整體驗證（JSON 格式、必填欄位、測試）再 commit。

**併發上限建議**：資料查證與測試類最多同時 3 個子代理（對應 3 筆來源 / 3 個案例），避免回收彙整反而塞車。

---

## 時間預估（序列 vs 平行對照）

| Task | 序列工時 | 平行後主代理實際佔用 | 說明 |
|------|----------|----------------------|------|
| Task 1 | 1 hr | 0（已完成） | — |
| Task 2 | 3 hr | ~1.5 hr | 第2層查證 3 子代理平行，主代理專注法規層 + 合併 |
| Task 3 | 3 hr | ~2 hr | 核心 match/calculate 主代理寫；其餘工具子代理草稿 |
| Task 4 | 1.5 hr | 1.5 hr | 主代理獨作，無法壓縮 |
| Task 5 | 1 hr | ~0（併入 Wave 2） | 與 Task 3 平行，不佔序列時間 |
| Task 6 | 2 hr | ~1.5 hr | 周邊草稿平行；部署本身純序列 |
| Task 7 | 2 hr | ~1.5 hr | 前端平行；Lambda 串接純序列 |
| Task 8 | 1.5 hr | ~0.5 hr | 3 案例平行，主代理只彙整 |
| Task 9 | 1 hr | ~0.5 hr | 素材平行產出 |

**序列總計約 16 小時 → 平行後關鍵路徑約 9~10 小時**（實際取決於子代理回收彙整速度與部署重試次數）。

---

## 關鍵決策

| 決策 | 理由 |
|------|------|
| Agent 程式碼放 `agent/` 而非 `app/career_navigator/` | 新起專案結構更乾淨，舊架構文件參考用 |
| CDK 放 `infra/` | 標準 monorepo 結構 |
| 資料靜態打包 | 比賽帳號無 DynamoDB，靜態 JSON 零依賴 |
| Lambda proxy 方案優先 | 最簡單的前端接入方式 |
| 使用 `strands-agents` SDK | 比賽指定技術棧 |
| 平行只用於獨立產物，合併一律主代理 | 避免同檔衝突與 schema 不一致，讓 fan-out 收益真正大於合併成本 |
| 部署類工作禁止平行 | 單一 AWS 沙盒環境，狀態互斥 |

---

## 風險與備案

| 風險 | 備案 |
|------|------|
| 比賽帳號 Lambda 權限不足 | 改用 Cognito Identity Pool + 前端直連 AgentCore |
| AgentCore 部署失敗 | 本地跑 Agent + ngrok 暴露 |
| 時間不夠做完 | 優先確保 Task 1-4-6-7 可 demo，資料用精簡版 |
| Exa MCP 掛掉 | graceful degradation，跳過即時搜尋 |
| 子代理回收彙整塞車 | 併發上限 3；合併是序列瓶頸，寧可少開也要保一致性 |
| 多子代理同改一檔造成衝突 | 鐵則：共享檔案落版只由主代理做，子代理僅交草稿 |

---

## 參考文件

- `docs/HANDOFF.md` — 專案全貌
- `docs/DATA_STRATEGY.md` — 資料三層策略
- `docs/RESOURCES_SCHEMA_PROPOSAL.md` — 新版 schema 設計
- `docs/CURRENT_DATA_ISSUES.md` — 現有資料錯誤
- `docs/TODO_NEXT_SESSIONS.md` — 原待辦清單
- `scraper/` — 法規擷取模組（可直接使用）
