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

### Task 3：實作六步驟 Career Tools　🧩+🚀 混合　✅ 已完成

**狀態**：已完成，報告 `docs/reports/TASK_3_REPORT.md`，commit `81886fb`。程式碼位置由 `agent/` 改為 `app/careernav/`（唯一真實來源，`agent/` 已標記 DEPRECATED，詳見 `docs/HANDOFF.md` 第三節）。

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

### Task 4：Agent 主程式與 System Prompt　🧩 主代理獨作　⚠️ 內容已隨 Task 3 完成，缺獨立報告

**狀態**：Task 3 為了讓工具能被 Runtime 載入，已同步完成本 Task 的核心產出（見 `docs/HANDOFF.md` 第一節「Task 3 順帶完成的部分」）。尚缺：獨立的 `docs/reports/TASK_4_REPORT.md`，以及確認驗收標準是否需微調（見下方）。

**目標**：完成 Agent 的編排邏輯與人設。

**產出**（已改為以下實際位置，非原規劃路徑）：
- `app/careernav/main.py` — 完整的 Agent 進入點（含 SYSTEM_PROMPT、agent_factory session cache）
- System Prompt 直接內嵌於 `main.py`（未拆獨立檔案，因 Runtime 只打包 `app/careernav/`）

**驗收**：原寫「本地 `python -m agent.main`」，因 `agent/` 已停用，應改為驗證 `app/careernav/main.py` 可正確 import 六個工具（已在 Task 3 用 strands venv 驗證 `TOOL_REGISTRY` 6 個工具正確註冊），或透過 `agentcore invoke` 端到端驗證（需先部署，見 `docs/DEPLOY_NOTES.md`）。

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

### Task 7：Lambda Proxy + 前端接入　🔒 純序列（前端 🚀 可平行）　📋 詳細施工計畫已定案（2026-08-01，與使用者確認）

**狀態**：需求與視覺風格已與使用者逐項確認（開場動畫、復古按鈕風格、對話狀態機、
時間軸視覺化），以下為完整施工計畫，取代本節原先的簡短描述。新 session 接續本
Task 時，直接依「七、施工順序」逐項執行即可，不需要重新與使用者討論已定案項目。

**目標**：讓瀏覽器可以透過 HTTP 跟 Agent 對話，且視覺風格為「黑底白字、標楷體、
復古 2D 遊戲按鈕」，並將 `generate_roadmap` 的結構化行動計畫渲染成可點擊連結的
橫式時間軸圖，而非純文字。

#### 一、整體架構

```
瀏覽器（純 HTML/CSS/JS，黑底白字復古風格，單一 frontend/index.html）
   │  POST /chat  { message, session_id }
   ▼
Lambda Function URL（AuthType.NONE，比賽現場需讓評審直接開網址，不設認證）
   │  boto3 bedrock-agentcore.invoke_agent_runtime()
   ▼
AgentCore Runtime（careernav_careernav-Su5fjSE2LM）
   │  SSE 事件流：文字 delta + 工具呼叫事件 + 工具回傳結果
   ▼
Lambda 解析 SSE，組出兩份東西回給前端：
   1. reply_text：組好的完整文字回覆（給對話氣泡顯示）
   2. roadmap：若這輪呼叫過 generate_roadmap，附上其原始結構化 JSON（給時間軸元件畫圖）
```

核心原則：**Lambda 是唯一負責「聽懂」Agent 內部事件流的地方**，前端只認兩種
簡單資料格式（一段文字、一份時間軸 JSON），不需要理解 SSE 或工具呼叫細節。

#### 二、Lambda Proxy 改寫規格（`lambda/proxy.py`）

**移除舊邏輯**：刪除 `bedrock-agent-runtime.invoke_agent` 呼叫（舊式 Bedrock
Agents API，跟目前的 AgentCore Runtime 不相容）、移除 `AGENT_ID` /
`AGENT_ALIAS_ID` 環境變數。

**新邏輯**：
- 改用 `boto3.client("bedrock-agentcore")`，呼叫 `invoke_agent_runtime()`：
  - `agentRuntimeArn`：從環境變數 `AGENT_RUNTIME_ARN` 讀取
  - `payload`：`json.dumps({"prompt": user_message}).encode()`
  - `contentType` / `accept`：`application/json`
- 已實測確認回應格式：`resp["response"]` 是可讀取串流物件，內容為 SSE 格式的
  多行 `data: {...}\n\n`，解析步驟：
  1. 逐行解析 `data: ` 開頭的 JSON
  2. 從 `event.contentBlockDelta.delta.text` 累積組出完整文字（最終文字回覆）
  3. **另外**盯著事件流中跟工具呼叫相關的部分，找出 `generate_roadmap` 工具的
     呼叫結果（**尚未實測，是本 Task 第一個要做的技術驗證，見第六節**）
- 回給前端的 JSON 格式：
  ```json
  {
    "reply": "完整文字回覆...",
    "session_id": "xxx",
    "roadmap": { ... generate_roadmap 的原始 JSON ... } 或 null（這輪沒呼叫到）
  }
  ```
- Lambda timeout 維持 90 秒（CDK 已設定）；前端另設 60 秒等待上限（見第五節）。
- AgentCore 呼叫失敗（逾時、例外）時回傳明確錯誤訊息，讓前端能顯示錯誤畫面
  而非卡在等待動畫。

**環境變數變更**：`infra/lib/stack.ts` 的 Lambda 環境變數從 `AGENT_ID` /
`AGENT_ALIAS_ID` 改成 `AGENT_RUNTIME_ARN`
（`arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM`），
並在 `agentRole` 新增 `bedrock-agentcore:InvokeAgentRuntime` 權限（目前只有
`bedrock:InvokeModel` 相關權限）。

**安全性決策（已與使用者確認）**：Function URL 維持 `AuthType.NONE`。理由：
比賽現場需讓評審直接開網址使用，不設認證卡關。代價：任何拿到網址的人都能
呼叫並產生 Bedrock 用量費用。此決策記入 `docs/reports/TASK_7_REPORT.md` 的
「已知風險」段落；比賽後若繼續對外開放，建議補 CloudFront + API Key header
或直接下線。

#### 三、前端檔案結構

單一 `frontend/index.html`（不引入建置工具，直接開瀏覽器可跑，方便丟到 S3），
內部用 `<style>` + `<script>` 內嵌：

```html
<style>/* 復古視覺樣式：配色變數、標楷體字型、按鈕邊框、掃描線動畫、時間軸樣式 */</style>
<body>
  <div id="boot-screen">...</div>     <!-- 開場逐行刷入畫面 -->
  <div id="home-screen">...</div>     <!-- 首頁：標題 + 開始對話按鈕 -->
  <div id="chat-screen">
    <div id="messages"></div>          <!-- 對話紀錄（含時間軸卡片） -->
    <div id="input-bar">...</div>      <!-- 輸入框 + 送出按鈕 -->
  </div>
</body>
<script>/* 狀態機切換、fetch 呼叫 Lambda、逐字顯示、時間軸渲染 */</script>
```

#### 四、視覺風格規格（已與使用者確認）

| 項目 | 規格 |
|------|------|
| 背景 / 文字 | 純黑 `#000000` 底、純白 `#FFFFFF` 字 |
| 字型 | `font-family: "標楷體", "DFKai-SB", "BiauKai", serif;`（非 Windows 裝置會 fallback 到 serif，效果打折，現場建議用 Windows 筆電） |
| 按鈕 | 雙層白色邊框（外框 2px 實線 + 內縮 3px 再一層 1px 線，模擬像素邊框）；按下時整體向右下位移 2px 並移除內層框線製造按壓感；hover 時文字閃爍或背景反白 |
| 對話氣泡 | 使用者訊息：右側白框方塊；Agent 回覆：左側白框方塊，用框線粗細/位置區分，不用顏色 |
| 等待動畫 | 簡化版（不分六步驟階段）：「▪▪▪」三方塊依序亮暗循環的跑馬燈 |
| 開場動畫 | 首頁每個區塊（標題/副標/按鈕）依序從上到下、每個間隔約 0.12 秒觸發淡入+輕微上移；**只在網頁第一次載入時跑一次**（用 `sessionStorage` 記 flag），「重新開始」按鈕不重播 |
| 文字顯示 | 逐字打字機效果，固定字元間隔（約每字 20~30ms），比照一般 AI 對話工具常見節奏 |
| 尺寸 | 只做筆電桌面尺寸（以 1280px 寬為基準），不寫 mobile media query |

#### 五、狀態機（已與使用者確認）

```
[載入] → [開場動畫，僅第一次] → [首頁] --點擊開始對話--> [對話畫面]
                                                              │
                                            使用者送出訊息 ──▶ [等待中：跑馬燈]
                                                              │
                              ┌────────────成功───────────────┤
                              ▼                               │
                  [逐字顯示 Agent 回覆]                        │
                  （若這輪有 roadmap 資料，                     │
                    文字顯示完後接著淡入時間軸卡片）              │
                              │                                │
                              ▼                                │
                       回到 [對話畫面]（可再輸入）                │
                                                                │
                              └───失敗/逾時(60秒)───────────────▶
                                    [錯誤訊息 + 重新發送按鈕]
```

補充規則：「等待中」狀態啟動 60 秒計時器，超過強制切到錯誤狀態；「重新發送」
重送同一則訊息；「重新開始」清空對話並切回首頁，不重播開場動畫。

#### 六、時間軸視覺化 — 資料流與渲染規格（已與使用者確認：橫式、直接嵌入對話串）

**資料契約（Lambda → 前端）**：`generate_roadmap`（`tools/logic.py`）原始回傳
結構直接轉發，不重新設計格式：
```json
{
  "status": "ok",
  "timeline": [
    { "month": 0, "label": "離職當週", "actions": [
      { "action": "...", "priority": "必要", "related_resource": "unemployment_benefit" }
    ]},
    ...
  ],
  "decision_points": ["第 1 個月需決定：..."],
  "courses": { "curated": [...], "hint": {...} },
  "total_months": 6
}
```

**連結來源**：使用者要求時間軸上要能點擊跳轉法條/補助/課程網址。
**建議做法**：不讓 Lambda 動態查詢，而是把 `resources.json`（6 筆）與
`courses.json`（3 筆）的精簡版（`id`/`name`/`source_url`/`law_references`）
直接打包進前端 JS 常數物件，時間軸渲染時用 `related_resource` id 查表取得
連結，不需額外網路請求。

**渲染規格（橫式時間軸）**：
- 橫向排列節點卡片，一個月份（或月份區間）為一節點，節點間用白色橫線串接
- 每節點：月份標籤 + 該月 `actions` 列表（標明 priority：必要/建議/決策點/里程碑）
- `priority === "決策點"` 或落在 `decision_points` 範圍的項目，用加粗/閃爍框線凸顯
- `action.related_resource` 有值時，該行文字變成可點擊連結（開新分頁）
- 課程建議（`courses.curated`）附在對應月份節點下方，同樣可點擊
- 節點區塊允許 `overflow-x: auto` 橫向捲動（保險措施，設計目標是 4~5 個節點在筆電螢幕內完整顯示）
- 出現時機：Agent 文字回覆逐字顯示完畢後，緊接著在同一則訊息下方淡入時間軸卡片

**技術風險與驗證方式（必須排在動工最前面）**：先用實際 invoke 測試一次觸發
`generate_roadmap` 的問題，確認：
1. AgentCore SSE 事件流裡工具呼叫的輸入/輸出用哪種事件類型傳遞（目前只實測
   過純文字 delta，見 `docs/reports/DEMO_TEST_RESULTS_20260801.md`，還沒實測
   帶工具呼叫結果的完整事件流）
2. 這個事件結構能否讓 Lambda 可靠抓到 `generate_roadmap` 的完整回傳 JSON

**備案**：若事件流解析不穩定（截斷、格式不可靠），改用「文字內嵌 JSON 標記」
方案——在 system prompt 加規則，要求 Agent 在文字回覆最後附加一段特定格式的
標記區塊（例如用 ` ```roadmap-data ... ``` ` 包住 roadmap JSON），Lambda 用正則
表達式抓出後從顯示文字中移除。這個方案不依賴事件流細節，較土法煉鋼但更穩定。
**技術驗證的結果決定用哪一種方案，需排在第一步做**。

#### 七、施工順序（Task 拆解，依序執行）

1. **技術驗證**：實測觸發 `generate_roadmap` 的 invoke，確認 SSE 事件流裡工具結果的抓取方式，決定用「事件流解析」或「文字內嵌 JSON 標記」方案
2. **Lambda 改寫**：`lambda/proxy.py` 換成 `invoke_agent_runtime`，解析文字 + roadmap 資料，加逾時/錯誤處理
3. **CDK 更新**：`infra/lib/stack.ts` 環境變數改 `AGENT_RUNTIME_ARN`，IAM Role 補 `InvokeAgentRuntime` 權限
4. **前端骨架**：狀態機切換邏輯（開場→首頁→對話→等待→錯誤→重置），先用純文字驗證整條鏈路能通（不做視覺樣式）
5. **前端視覺**：套上黑底白字標楷體 + 復古按鈕邊框 + 開場逐行刷入動畫 + 等待跑馬燈
6. **逐字顯示**：文字打字機效果
7. **時間軸元件**：橫式時間軸渲染 + resource/course 連結對照表 + 淡入嵌入對話串
8. **部署驗證**：同步到 `~/careernav`，部署 CDK stack（Lambda + S3，若比賽帳號權限允許），或視部署環境限制決定是否改用替代方案（見第八節風險 1）
9. **端到端測試**：至少 2 個案例（含一個會觸發 `generate_roadmap` 的完整流程），確認文字、時間軸、連結、錯誤情境都正常
10. **報告**：`docs/reports/TASK_7_REPORT.md`，記錄安全性風險（Function URL 無認證）、技術驗證結果（用了哪個方案）、已知限制，然後 commit

#### 八、已知風險（提前記錄，避免下個 session 重新踩坑）

1. **比賽帳號權限未知**：`docs/TODO_NEXT_SESSIONS.md` 提過比賽帳號可能缺
   Lambda/API Gateway 權限，`infra/` 的 CDK 部署到目前為止還沒實際跑過。動工
   第一步（施工順序 8）要先確認 Lambda + Function URL 能否在目前帳號建立成
   功，若不行需要討論備案（例如本機跑 Lambda 邏輯 + ngrok，或前端用瀏覽器
   SigV4 簽名直連 AgentCore，即 `TODO_NEXT_SESSIONS.md` T1 提過的替代方案）。
2. **SSE 事件流解析是未知數**：第六節的技術風險，可能導致改用「文字內嵌
   JSON 標記」備案，這會需要微調 system prompt。
3. **標楷體字型**：非 Windows 裝置會 fallback 到 serif，現場若用非 Windows
   筆電操作，視覺效果會打折。

**產出檔案清單**：
- `lambda/proxy.py`（改寫）、`lambda/requirements.txt`
- `infra/lib/stack.ts`（環境變數 + IAM 權限更新）
- `frontend/index.html`（完整重寫，取代目前的骨架版）
- `docs/reports/TASK_7_REPORT.md`（新增）

**驗收標準**：瀏覽器打字 → 收到 Agent 完整回覆（逐字顯示）；觸發 roadmap 的
問題會額外顯示可點擊的橫式時間軸；等待超過 60 秒或發生錯誤時顯示明確錯誤畫面
與重試按鈕；CloudWatch 無新增 ERROR/Exception。

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
