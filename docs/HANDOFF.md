# 職涯導航家（CareerNav）— 專案交接文件

> 最後更新：2026-07-29
> 用途：讓任何新 session / 新成員在 5 分鐘內掌握此專案全貌

---

## 一、專案目的

參加 **2026 雲湧智生：臺灣生成式 AI 應用黑客松**（TIARA 臺灣半導體產學研發聯盟出題）。

核心問題：台灣半導體/製造業 AI 化導致中高齡、藍領、服務業勞工失業，但政府補助資訊散落、門檻高、職訓預算執行率不到 30%。

產品：一站式 AI 對話 Agent — 使用者用一句話描述狀況，Agent 自動跑六步驟產出完整轉職行動計畫。

---

## 二、技術架構

```
瀏覽器 (frontend/index.html，未在此 repo)
    │ HTTP POST
    ▼
Lambda: careernav-chat-proxy (proxy_lambda/app.py)
    │ boto3 + SigV4
    ▼
Amazon Bedrock AgentCore Runtime
    ├── Strands Agent + Claude Sonnet 4.5
    ├── 6 Career Tools (tools/career_tools.py)
    ├── MCP Client → Exa AI 網路搜尋
    └── AgentCore Memory (內建對話記憶)
```

### 核心技術棧

| 層 | 技術 |
|---|---|
| Agent 框架 | `strands-agents` (Python) |
| LLM | Claude Sonnet 4.5 via Bedrock |
| 託管 | Amazon Bedrock AgentCore (CodeZip, Python 3.14) |
| 基礎設施 | AWS CDK (`@aws/agentcore-cdk`) |
| 即時搜尋 | Exa AI via MCP Client |
| 部署 CLI | `agentcore deploy` |

---

## 三、六步驟 Pipeline

| # | Tool | 輸入 | 輸出 |
|---|------|------|------|
| 1 | `analyze_profile` | 自然語言描述 | 結構化背景（年齡/產業/年資/離職原因等） |
| 2 | `match_resources` | 背景欄位 | 符合資格的補助方案清單 |
| 3 | `calculate_benefit` | matched_ids + 月投保薪資 | 每月/總計金額試算 |
| 4 | `generate_roadmap` | matched_ids + 訓練意願 | 1~6 個月時間軸 |
| 5 | `get_checklist` | matched_ids | 應備文件清單 |
| 6 | `send_notification` | email + summary | Email 通知（目前 demo 模擬） |

---

## 四、目前狀態

### 已完成 ✅

- Agent 六步驟邏輯完整
- 8 筆示範用補助資料 (`resources.json`)
- `agentcore deploy` 部署成功（stack: `AgentCore-careernav-default`）
- CLI `agentcore invoke` 測試通過
- Lambda proxy 程式碼寫好 + 部署腳本
- 前端聊天頁面雛型（不在此 repo）

### 卡住 ❌

- **前端接入**：瀏覽器→Agent 的連線被帳號政策擋住
  - Lambda Function URL (auth-type NONE) → 403
  - API Gateway → 帳號無權限
  - CloudFront → 查詢被擋，建立未確認
- **資料品質**：8 筆 mock 中有 6 筆金額/條件錯誤（詳見 `CURRENT_DATA_ISSUES.md`）

### 關鍵限制

- 比賽帳號是 AWS Workshop Studio 沙盒（帳號 `893083750609`）
- 缺 DynamoDB、API Gateway、SES、SNS
- 正式比賽當天會發新帳號，權限可能不同

---

## 五、檔案結構

```
careernav/
├── HANDOFF.md                    ← 本文件（交接用）
├── DATA_STRATEGY.md              ← 資料來源策略
├── DATA_SOURCES_VERIFIED.md      ← 經實測的資料源清單
├── RESOURCES_SCHEMA_PROPOSAL.md  ← 新版 schema 設計
├── CURRENT_DATA_ISSUES.md        ← 現有資料錯誤對照
├── TODO_NEXT_SESSIONS.md         ← 待辦事項（優先序）
├── PROJECT_OVERVIEW.md           ← 原專案結構化介紹
├── PROGRESS.md                   ← 開發進度紀錄
├── DATA_SOURCES.md               ← 原始資料規劃（未實測前）
├── AGENTS.md                     ← AgentCore CLI 使用說明
├── README.md                     ← AgentCore 預設 README
├── agentcore/
│   ├── agentcore.json            ← 專案宣告（runtime + memory）
│   ├── aws-targets.json          ← 部署目標帳號
│   └── cdk/                      ← CDK 基礎設施（TypeScript）
├── app/career_navigator/
│   ├── main.py                   ← 進入點（Agent 編排）
│   ├── model/load.py             ← Bedrock 模型載入
│   ├── memory/session.py         ← AgentCore Memory 整合
│   ├── mcp_client/client.py      ← Exa AI MCP 客戶端
│   ├── tools/career_tools.py     ← 六步驟工具實作
│   ├── data/resources.json       ← 補助資料（8 筆，待修正擴充）
│   └── pyproject.toml            ← Python 依賴宣告
├── proxy_lambda/app.py           ← Lambda 轉接站
└── deploy_proxy.sh               ← Lambda 部署腳本
```

---

## 六、快速接手指南

### 如果要繼續開發資料層

1. 先讀 `DATA_STRATEGY.md` 了解三層策略
2. 讀 `CURRENT_DATA_ISSUES.md` 了解現有資料哪裡錯
3. 讀 `RESOURCES_SCHEMA_PROPOSAL.md` 了解新 schema
4. 開始擴充 `resources.json`

### 如果要解決前端接入

1. 讀 `PROGRESS.md` 的「目前卡住的地方」
2. 最可行方案：Cognito Identity Pool 發臨時憑證 → 前端 AWS SDK for JS 做 SigV4
3. 帳號有 `cognito-idp:*`，但需確認是否包含 Identity Pool

### 如果比賽當天拿到新帳號

1. 跑權限檢查：`aws iam list-attached-role-policies --role-name WSParticipantRole`
2. 確認 Bedrock AgentCore、Lambda、Cognito 可用
3. 重跑 `agentcore deploy`
4. 前端接入方案依帳號權限決定

---

## 七、相關文件索引

| 文件 | 用途 |
|------|------|
| `DATA_STRATEGY.md` | 資料從哪來、怎麼整理、用在哪 |
| `DATA_SOURCES_VERIFIED.md` | 每個資料源的實測結果和範例 |
| `RESOURCES_SCHEMA_PROPOSAL.md` | 新 schema 讓金額/條件分支表達正確 |
| `CURRENT_DATA_ISSUES.md` | 現有 8 筆資料的逐筆勘誤表 |
| `TODO_NEXT_SESSIONS.md` | 所有待辦依優先序排列，含工時預估 |
| `PROJECT_OVERVIEW.md` | 原始完整專案介紹 |
| `PROGRESS.md` | 完整開發歷程紀錄 |
