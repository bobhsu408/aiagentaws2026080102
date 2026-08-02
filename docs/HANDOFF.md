# 職涯導航家（CareerNav）— 專案交接文件

> ⚠️ **本檔案的「Task 7 進度」章節已過期（寫於步驟 6 進行中的暫停點）。**
> **Task 7 已於 2026-08-02 全部完成。要接手維護請先讀 → [`docs/CURRENT_STATUS.md`](CURRENT_STATUS.md)**
>
> 本檔案保留作為 Task 1～6 的歷史脈絡與決策紀錄，仍有參考價值
> （尤其第四節部署路徑限制、第五節已解決問題），但「目前狀態」一律以
> `CURRENT_STATUS.md` 為準。

> 最後更新：2026-08-02（Task 7 施工中，完成步驟 1~5，步驟 6 進行中）← 已過期，見上方
> 用途：讓新 session 直接依正式計畫接續，不重做、不跳步、不用重讀大量歷史文件

## 新 session 的第一句指令

**維護既有功能**：先讀 `docs/CURRENT_STATUS.md`，該檔含線上資源清單、
架構圖、維護指令、雷區清單。

**接續未完成的 Task 8～9**：

> 請依 `docs/IMPLEMENTATION_PLAN_20250731.md` 接續 Task 8。目前狀態見 `docs/CURRENT_STATUS.md`，Task 1~7 均已完成，不需重做。

<details>
<summary>（已過期）原本的 Task 7 接續指令</summary>

> 請接續 Task 7（Lambda Proxy + 前端接入），依 `docs/IMPLEMENTATION_PLAN_20250731.md` 第七節「七、施工順序」逐項執行。目前進度見本檔案第一之一節，直接從「下一步」開始，不需要重新確認已定案的視覺/狀態機/時間軸規格。

</details>

## 一、正式進度與下一步

唯一正式計畫：`docs/IMPLEMENTATION_PLAN_20250731.md`。

| 項目 | 狀態 |
|------|------|
| Task 1：專案基礎設施設置 | 已完成，報告：`docs/reports/TASK_1_REPORT.md`，commit：`891e21a` |
| Task 2：實作 `resources.json` 與 `constants.json` | 已完成（MVP 範圍，見下方說明），報告：`docs/reports/TASK_2_REPORT.md` |
| Task 3：實作六步驟 Career Tools | **已完成**，報告：`docs/reports/TASK_3_REPORT.md`，commit：`81886fb` |
| Task 4：Agent 主程式與 System Prompt | **副產品已完成**，見下方「Task 3 順帶完成的部分」，尚無獨立報告 |
| Task 5：MCP Client 整合（Exa AI） | **已完成**，報告：`docs/reports/TASK_5_REPORT.md` |
| Task 6：CDK 基礎設施完善 + AgentCore 部署 | **已完成**，報告：`docs/reports/TASK_6_REPORT.md`。`infra/` 已於 Task 7 步驟 8 實際 `cdk deploy` 完成（Lambda + 私有 S3 + CloudFront） |
| Task 7：Lambda Proxy + 前端接入 | **已完成**（十步驟全部），報告：`docs/reports/TASK_7_REPORT.md`。**下方「一之一」章節為施工中的舊快照，已過期，現況見 `docs/CURRENT_STATUS.md`** |
| 語音輸入（額外項目，非計畫內） | 已完成（另一 session），報告：`docs/reports/VOICE_INPUT_REPORT.md` |
| Task 8～Task 9 | 尚未依正式計畫完成 |

Runtime 已於 Task 7 步驟 1 重新部署，**線上程式碼含 Task 7 對 `main.py` 的新改動**（攔截 `generate_roadmap` 工具結果並額外轉發），已用 boto3 直接呼叫 + `agentcore invoke` 實測正常。

## ~~一之一、Task 7 詳細進度~~（⚠️ 已過期的舊快照，勿依此施工）

> **這一節寫於 Task 7 步驟 6 進行中的暫停點，內容已不反映現況。**
> Task 7 十個步驟已全部完成，且最終架構與這裡描述的不同
> （例如：Function URL 不再是 `AuthType.NONE`、前端不再打 Function URL 而是
> 打同源 `/chat`、逐字打字機已改為逐區塊淡入）。
>
> **現況請看 [`docs/CURRENT_STATUS.md`](CURRENT_STATUS.md)，
> 技術決策理由看 [`docs/reports/TASK_7_REPORT.md`](reports/TASK_7_REPORT.md)。**
>
> 以下內容僅保留作為「當時如何解決 SSE 抓不到工具結果」的技術紀錄，
> 那部分（`main.py` 攔截 `ToolResultMessageEvent`）至今仍有效。

### （以下為舊快照）Task 7 詳細進度（施工順序十步驟，2026-08-02 暫停點）

**已完成（步驟 1~5）：**

1. **技術驗證**✅ — 用 boto3 直接呼叫正式 Runtime 的 `invoke_agent_runtime`，抓原始 SSE 事件流分析（存於 `/tmp/raw_sse_output.txt`，該機器 `/tmp` 為暫存，新機器/新 session 不會存在，需要重跑才能複現）。**結論**：AgentCore SSE 串流原生只轉發工具「輸入參數」delta，完全不含工具「執行結果」（在 123KB 原始輸出中搜尋 `timeline`/`decision_points` 是 0 筆）。改用「main.py entrypoint 攔截 `ToolResultMessageEvent`」方案（不是計畫原先設想的文字內嵌 JSON 標記備案，效果更好更穩定）：在 `app/careernav/main.py` 的 `invoke()` 裡記錄 `contentBlockStart` 事件的 `toolUseId -> name` 對照表，遇到 event 帶 `message.role == "user"` 且 content 有 `toolResult` 時，比對 `toolUseId` 找出 `tool_name`，若屬於 `generate_roadmap` 就把 `toolResult.content[].text` 解析成 JSON，包成自訂事件 `{"careernav_tool_result": {"name": ..., "data": {...}}}` 額外 yield 出去。**已在正式 Runtime 重新部署並實測確認可用**（`careernav_tool_result` 事件在真實 SSE 流中出現，內容與 `tools/logic.py` 的 `generate_roadmap` 回傳完全吻合）。

2. **Lambda 改寫**✅ — `lambda/proxy.py` 已全面改寫，用 `boto3.client("bedrock-agentcore").invoke_agent_runtime()`，解析上述 SSE 格式組出 `{"reply": ..., "session_id": ..., "roadmap": ... 或 null}`。加了 read timeout（75 秒，低於 Lambda 90 秒總 timeout）、`_normalize_session_id()` 補齊過短的 session_id（AgentCore `runtimeSessionId` 最短 33 字元限制）、三種錯誤處理（`BotoCoreError`/`ClientError`、非預期例外、空回應）。**已用真實請求做 end-to-end 測試**（不是 mock），含觸發 `generate_roadmap` 的案例，`roadmap` 欄位正確帶出 `timeline`/`decision_points`/`courses`/`total_months`。

3. **CDK 更新**✅ — `infra/lib/stack.ts`：`agentRole` 新增 `bedrock-agentcore:InvokeAgentRuntime` policy；Lambda 環境變數從 `AGENT_ID`/`AGENT_ALIAS_ID` 改為 `AGENT_RUNTIME_ARN`（硬編碼實際值，因為 AgentCore Runtime 由獨立 `agentcore` CLI 管理，不屬於此 CDK stack 的資源，不能用 cross-stack 參照）。已在 `~/careernav/infra` 跑 `npm install` + `npx cdk synth` 成功產出完整 CloudFormation template。**尚未 `cdk deploy`**（刻意留給步驟 8 統一處理，因為要等前端也做完才一次部署驗證整條鏈路，避免重複部署）。

4. **前端骨架**✅ — `frontend/index.html` 從 Task 1 的極簡骨架改寫成完整狀態機（`home` → `chat` → `waiting`/`error`，對應計畫第五節狀態機圖）。`API_ENDPOINT` 目前是 placeholder 字串 `"PLACEHOLDER_LAMBDA_FUNCTION_URL"`，**要等步驟 8 `cdk deploy` 拿到真正 Function URL 後才能填入**做真實瀏覽器測試。

5. **前端視覺**✅ — 疊上復古視覺樣式：黑底白字、`font-family: "標楷體","DFKai-SB","BiauKai",serif`、雙層像素邊框按鈕（`::after` 偽元素做內縮邊框，`:active` 位移 2px 模擬按壓感）、開場逐項淡入動畫（`enterHomeScreen()` 用 `sessionStorage` key `cn_booted` 判斷只播一次，`resetConversation()` 明確移除 `play-intro` class 避免重播）、等待跑馬燈（3 個 `.marquee-dot` 依序 delay 循環閃爍）。**未破壞 Task 4 的狀態機邏輯**（所有 function/id 簽名不變）。

**進行中（步驟 6，尚未完成）：**

6. **逐字顯示（文字打字機效果）**⚠️ **只做了一半**：目前只在 `frontend/index.html` 加了設定常數 `const TYPE_INTERVAL_MS = 25;`（每字 25ms，符合規格 20~30ms），**但還沒有把它接到 `appendMessage()`**——`appendMessage("agent", text)` 目前仍是直接 `bubble.textContent = text` 一次性賦值，不是逐字插入。**新 session 接續時**：
   - 需要寫一個逐字插入的函式（例如 `typeText(bubble, text, intervalMs)`，用 `setInterval` 或遞迴 `setTimeout` 逐字附加），只用在 Agent 回覆（`role === "agent"`），使用者自己送出的訊息維持立即顯示。
   - **注意計畫規則**：「若這輪有 roadmap 資料，文字顯示完後接著淡入時間軸卡片」——所以 `sendMessage()` 裡呼叫 `appendMessage("agent", ...)` 後，`appendRoadmapPlaceholder(data.roadmap)` 必須等文字打字動畫完全跑完才觸發，不能同時出現。目前的同步呼叫寫法需要改成等待打字機 Promise/callback 完成後才呼叫。
   - 改完後要重跑 `/tmp/frontend_test/run_test.js`（jsdom 行為測試，見下方「測試環境備忘」）確認沒有破壞既有 21 項斷言，並視情況新增打字機相關的斷言（例如用 `jest.useFakeTimers` 風格手動 fast-forward，或直接測試 `typeText` 函式本身的行為）。

**尚未開始（步驟 7~10）：**

7. 時間軸元件：橫式時間軸渲染 + resource/course 連結對照表 + 淡入嵌入對話串（目前 `appendRoadmapPlaceholder()` 只是文字佔位，要換成計畫第六節規格的完整卡片渲染）。
8. 部署驗證：同步到 `~/careernav`，執行 `cdk deploy`（Lambda + S3），拿到 Function URL 填入前端 `API_ENDPOINT`。
9. 端到端測試：至少 2 個案例（含一個觸發 `generate_roadmap`），在真實瀏覽器或至少用 curl/fetch 對正式 Function URL 測試。
10. 報告：`docs/reports/TASK_7_REPORT.md`（記錄安全性風險：Function URL `AuthType.NONE` 無認證；技術驗證結果：SSE 不含 toolResult，改用攔截方案；已知限制：標楷體字型 fallback 等），然後 commit。

### 測試環境備忘（避免新 session 重新摸索）

- **workspace 是 `noexec` 磁碟**：npm/cdk/agentcore CLI 必須在 `~/careernav`（rsync 副本）執行，不能在 workspace 直接跑。同步指令見本檔案第四節。
- **AWS credentials**：`cd ~/careernav && set -a && source .env && set +a`。
- **Python 測試 venv**：`~/careernav_venv`（python3.14），已額外 `pip install bedrock-agentcore`（原本沒裝，本機測試 `main.py` 的 `invoke()` 需要這個套件）。
- **前端 jsdom 測試**：`/tmp/frontend_test/`（`npm install jsdom` 完成），測試腳本 `/tmp/frontend_test/run_test.js`，用 `node /tmp/frontend_test/run_test.js` 執行，目前 21 項斷言全過。**`/tmp` 是暫存目錄，新機器/新 session 這個資料夾不會存在**，若要重跑測試需要重新 `mkdir -p /tmp/frontend_test && cd /tmp/frontend_test && npm init -y && npm install jsdom`，測試腳本內容可從本次 session 的對話記錄重建，或直接重寫（測試涵蓋：初始狀態、開場動畫只播一次、開始對話、送出訊息含 roadmap 渲染、伺服器錯誤、重新發送、網路失敗、重新開始清空對話）。
- **視覺驗證用本機 `google-chrome --headless=new`**：`google-chrome --headless=new --disable-gpu --no-sandbox --screenshot=/tmp/xxx.png --window-size=1280,900 --virtual-time-budget=3000 --run-all-compositor-stages-before-draw "file:///path/to/frontend/index.html"`，可用來確認 CSS 動畫跑完後的最終畫面。
- **正式 Runtime 驗證腳本**：`invoke_agent_runtime` 的 boto3 呼叫範例（含 SSE 解析）已寫入 `lambda/proxy.py` 本體，可直接 `import proxy; proxy._parse_sse_stream(raw_bytes)` 單獨測試解析邏輯，不需要每次都重新發真實請求。

### Task 7 關鍵技術事實（給 Lambda/前端後續維護參考）

- Runtime ARN：`arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM`
- boto3 呼叫：`client("bedrock-agentcore", region_name="us-west-2").invoke_agent_runtime(agentRuntimeArn=..., runtimeSessionId=(需 33~256 字元), payload=json.dumps({"prompt": text}).encode(), contentType="application/json", accept="application/json")`
- 回應 `resp["response"]` 是可讀取串流物件，`.read()` 拿到完整 bytes，內容為 `text/event-stream`，每行 `data: {json}\n\n`：
  - `{"event": {"contentBlockDelta": {"delta": {"text": "..."}}}}` → 累積組成文字回覆
  - `{"event": {"contentBlockDelta": {"delta": {"toolUse": {"input": "..."}}}}}` → 工具輸入參數片段，非回覆文字，Lambda 已正確忽略
  - `{"careernav_tool_result": {"name": "generate_roadmap", "data": {...}}}` → `main.py` 新增的自訂事件，Lambda 直接取 `data` 當 `roadmap` 回傳給前端

### Task 6 重點提醒（避免下個 session 重踩坑）

- 上次部署失敗是因為在 workspace（`noexec` 磁碟）執行部署指令；一律在 `~/careernav` 執行 `agentcore deploy`，先用 `docs/DEPLOY_NOTES.md` 的安全同步指令同步程式碼。
- 本次部署只更新了 AgentCore Runtime（`agentcore/cdk/`）。`infra/lib/stack.ts`（Lambda proxy + S3 前端）**仍未部署**，屬 Task 7 範圍。
- 部署後務必用 `agentcore invoke` 實際測試 + 查 CloudWatch 確認無 ImportError，不要只看 `agentcore status` 顯示 READY 就當作完成（READY 只代表容器啟動成功，不保證程式邏輯正確載入）。

### Task 5 重點提醒（避免下個 session 重踩坑）

- MCP Client 套件位於 `app/careernav/exa_mcp/`，**刻意不叫 `mcp/`**：
  `main.py` 會把 `app/careernav/` insert 進 `sys.path` 最前面，若資料夾叫
  `mcp` 會蓋掉 PyPI 上 strands 依賴的 `mcp`（Model Context Protocol SDK）
  本身，導致 `ModuleNotFoundError: No module named 'mcp.client'`（已實測
  重現）。詳見 `docs/reports/TASK_5_REPORT.md` 第四節。
- 只開放 Exa 預設兩個工具：`web_search_exa`、`web_fetch_exa`。用
  `MCPClient(continue_on_error=True)` 做 graceful degradation，連不上時
  Agent 仍能用其餘六個 Career Tools 正常運作。
- `EXA_API_KEY` 留空即可運作（keyless，有速率限制）；若要提高額度，
  Exa 官方目前唯一支援的傳遞方式是 URL query string，沒有 header 替代
  方案，這是已知風險，不是本專案程式碼可規避的。

### Task 3 順帶完成的部分（重要，避免重做 Task 4）

Task 3 為了讓六步驟工具能被 Runtime 實際載入，已將 `app/careernav/main.py` 改寫為：
- `SYSTEM_PROMPT` 完整版（六步驟引導、回覆規範、易錯事實提醒）
- `agent_factory()` session LRU cache、`NullConversationManager`
- `from tools.career_tools import TOOL_REGISTRY` 正式載入六個工具

這正是 Task 4 的核心產出（「Agent 的編排邏輯與人設」）。**未完成的只有**：
- Task 4 原驗收標準寫的是「本地 `python -m agent.main` 可啟動」——`agent/` 已於 Task 3 標記 DEPRECATED，此驗收標準需改為 `python -m app.careernav.main`（或改用 `agentcore invoke` 驗證，見第五節）。
- 尚未針對 Task 4 單獨寫 `docs/reports/TASK_4_REPORT.md`。

**建議下一個 session**：先確認 `app/careernav/main.py` 的 system prompt 是否需要調整，若無異議就補一份簡短的 TASK_4_REPORT.md（引用 Task 3 的變更），再進 Task 5。不要重新設計一次 system prompt。

### Task 2 範圍調整說明（重要，影響後續 Task）

原計畫要求 15~20 筆資料求全。與使用者討論後改為 **MVP 情境反推法**：比賽主題是「因應高齡化的人力結構與人力發展」，因此重新設計三個情境並聚焦其中一個先做：

- **情境 A（已建立資料）**：58 歲工廠作業員因產線自動化被資遣，距退休 7 年，體力已無法再做同類工作 → 技能斷層與轉銜。`resources.json` 目前 **6 筆**，全部對應此情境：`unemployment_benefit`、`training_living_allowance`、`early_reemployment_bonus`、`relocation_transport_subsidy`、`relocation_moving_subsidy`、`relocation_rent_subsidy`。
- **情境 B（尚未建立資料）**：小型工廠雇主想僱用中高齡被裁員者，關注僱用成本 → 企業端人力發展（對應 `mid_age_employment_subsidy_employer` 類資料，`recipient: 雇主`）。
- **情境 C（尚未建立資料）**：62 歲高齡者由子女代為操作系統查詢 → 高齡者再就業 + **介面可及性**（打字對此族群是負擔，暗示 Task 4 system prompt 需支援「代理人敘述」、Task 7 前端需考慮簡化流程/語音輸入，但這屬 UX 決策，尚未定案，留待 Task 4/7 討論）。

**下一個 session 若要擴充情境 B、C 的資料**，可依 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 2 平行策略開子代理查證（僱用獎助已在法規中確認，健保費補助、職務再設計也已核對，可直接補寫；產業新尖兵/微型創業鳳凰等第 2 層行政計畫類資料才需要子代理查官網）。

## 二、目前可用的 AWS Runtime

- Region：`us-west-2`
- Account：`881768789243`
- Model：`us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- AgentCore CLI：`0.25.0`
- Stack：`AgentCore-careernav-default`
- Runtime ID：`careernav_careernav-Su5fjSE2LM`
- Runtime ARN：`arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM`
- Runtime 狀態：`READY`
- `agentcore invoke`：已成功回覆繁體中文

部署檢查點報告：`docs/reports/AGENTCORE_RUNTIME_DEPLOYMENT_REPORT.md`。

## 三、目前實際架構

```text
AgentCore CLI
  └── agentcore/agentcore.json
       └── CodeZip: app/careernav/          ← 唯一真實來源（Task 3 已定案）
            ├── main.py                     # Runtime 入口：載入 tools.career_tools.TOOL_REGISTRY
            ├── pyproject.toml              # Runtime 依賴
            ├── data/
            │   ├── resources.json          # 情境 A，6 筆補助資料
            │   ├── constants.json          # 2026 基本工資等常數
            │   └── courses.json            # 3 筆計畫層級課程樣本
            ├── tools/
            │   ├── career_tools.py         # 六個 @tool 薄封裝
            │   ├── logic.py                # 純業務邏輯（零 strands 依賴，方便測試）
            │   ├── data_loader.py          # 資料載入 + 模組快取
            │   ├── formula.py              # ast 白名單公式/條件求值（不用 eval）
            │   └── profile.py              # profile schema + 欄位對應表 + 啟發式萃取
            └── tests/
                └── test_career_tools.py    # 15 個單元測試，全數通過

端到端架構（程式碼已完成，尚未部署 Lambda/S3，見「一之一」節）
瀏覽器 → Lambda proxy (lambda/proxy.py) → AgentCore Runtime → Strands Agent → Career Tools
```

### 兩套 Agent 程式碼的現況（Task 3 已解決，勿重新討論）

- **`app/careernav/`：唯一真實來源**，也是 AgentCore CLI 實際打包部署的目錄。六步驟工具與所有資料都在這裡。
- **`agent/`：已停用（DEPRECATED）**，見 `agent/DEPRECATED.md`。保留僅供歷史參考，**不要在此新增或修改程式碼**，也不要把資料改回搬到這裡。

如果之後要改工具或資料，一律在 `app/careernav/` 下修改。

## 四、部署路徑限制

Workspace 位於：

```text
/media/data/共用文件/專案開發/aws/hoyilive
```

此磁碟以 `noexec` 掛載，不能執行 npm 安裝的 `esbuild` binary。因此：

- 開發與 Git：在 workspace 路徑操作
- npm/CDK/AgentCore 部署：同步到 `~/careernav` 後操作

安全同步指令：

```bash
rsync -av --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='cdk.out' \
  --exclude='agentcore/.cli' \
  "/media/data/共用文件/專案開發/aws/hoyilive/" \
  "$HOME/careernav/"
```

`agentcore/.cli` 必須保留部署目錄中的版本，因為它包含 Runtime deployment state。

部署與驗證：

```bash
cd ~/careernav
export PATH="$HOME/.local/bin:$PATH"
set -a
source .env
set +a
agentcore validate
agentcore deploy --yes --verbose
agentcore status --json
agentcore invoke "你好" --json
```

完整說明：`docs/DEPLOY_NOTES.md`。

## 五、本階段已解決的問題

最初 invoke 回傳：

```text
Runtime initialization time exceeded
```

CloudWatch 的真正原因不是冷啟動，而是：

```text
ImportError: cannot import name 'tool' from 'strands.types.tools'
```

已將以下檔案改為從 Strands 頂層匯入 `tool`：

- `app/careernav/main.py`
- `agent/tools/career_tools.py`

正確寫法：

```python
from strands import Agent, tool
```

重新部署後 invoke 成功，最近一次驗證期間 CloudWatch 沒有新的 ERROR、Traceback、ImportError 或 Exception。

## 六、尚未完成與已知風險

1. **Lambda/S3 尚未部署**：`infra/` stack 已 `cdk synth` 驗證過範本，尚未 `cdk deploy`，見「一之一」步驟 8。
2. **前端 API_ENDPOINT 是 placeholder**：`frontend/index.html` 的 `API_ENDPOINT` 常數要等 `cdk deploy` 拿到 Function URL 才能填入。
3. **Memory 尚未啟用**：`agentcore/agentcore.json` 現在的 `memories` 為空陣列。
4. **AWS Session Token 有效期有限**：若出現 `ExpiredToken`，更新 workspace 與 `~/careernav` 的 `.env`。
5. **Credentials 不得 commit**：`.env` 已由 `.gitignore` 排除。
6. **資料範圍僅涵蓋情境 A**：情境 B（雇主僱用中高齡）、情境 C（高齡者+代理人操作）尚無對應 `resources.json` 資料，Task 8 端到端測試前需決定是否補齊。
7. **課程資料僅 3 筆計畫層級樣本**：`app/careernav/data/courses.json` 是穩定資訊，即時開課梯次由 Exa MCP 補（`generate_roadmap` 已預留 `course_hint`／`hint.keywords` 欄位供即時搜尋使用）。
8. **LINE 通知尚未啟用**：`send_notification` 目前為展示用 email 純模擬（`channel: "email"`, `demo_mode: true`）。介面已預留 `line_user_id` 參數；待取得 LINE Channel Access Token 後可加真推播＋自動降級模擬（`.env.example` 已加 `LINE_CHANNEL_ACCESS_TOKEN`／`LINE_DEMO_USER_ID` 欄位待填）。
9. **`agent/` 目錄已停用**：不要再修改或讀取 `agent/` 下的程式碼與資料，一律在 `app/careernav/` 操作（見 `agent/DEPRECATED.md`）。
10. **Function URL 無認證**：計畫已定案維持 `AuthType.NONE`（比賽現場需讓評審直接開網址），此風險會記入 `docs/reports/TASK_7_REPORT.md`。

## 七、下一個 session 應執行

**直接接續 Task 7 步驟 6（逐字打字機效果）**，見本檔案「一之一」節第 6 點的詳細說明。完成後依序做步驟 7（時間軸元件）、8（部署驗證）、9（端到端測試）、10（報告 + commit）。

**若要驗證六步驟工具邏輯**（不需要重讀大量文件）：
```bash
cd app/careernav
~/careernav_venv/bin/python -m pytest tests/ -q   # 若無此 venv，見下方建立指令
```
建立測試 venv（若尚未建立）：
```bash
python3 -m venv ~/careernav_venv
~/careernav_venv/bin/pip install --quiet pytest strands-agents bedrock-agentcore
```

**若要重新驗證 Lambda 解析邏輯**（不需要重新部署或發真實請求）：
```bash
cd lambda
~/careernav_venv/bin/python -c "
import proxy
# proxy._parse_sse_stream(raw_bytes) 可單獨測試 SSE 解析
# proxy._normalize_session_id(session_id) 可單獨測試 session id 補齊
"
```

## 八、重要文件

| 文件 | 用途 |
|------|------|
| `docs/IMPLEMENTATION_PLAN_20250731.md` | 唯一正式 Task 順序與驗收標準（Task 7 施工順序見該檔第七節） |
| `docs/reports/TASK_1_REPORT.md` | Task 1 完成證據 |
| `docs/reports/TASK_2_REPORT.md` | Task 2 完成證據（含情境 A 範圍調整說明） |
| `docs/reports/TASK_3_REPORT.md` | Task 3 完成證據（六步驟工具設計決策、測試結果） |
| `docs/reports/AGENTCORE_RUNTIME_DEPLOYMENT_REPORT.md` | Runtime 部署檢查點 |
| `docs/reports/TASK_7_REPORT.md` | **尚未建立**——待 Task 7 步驟 10 撰寫 |
| `docs/DEPLOY_NOTES.md` | 雙路徑部署操作手冊 |
| `docs/RESOURCES_SCHEMA_PROPOSAL.md` | Task 2 schema 依據 |
| `docs/CURRENT_DATA_ISSUES.md` | 錯誤資料清單 |
| `docs/DATA_SOURCES_VERIFIED.md` | 已驗證資料來源 |
| `agent/DEPRECATED.md` | 說明舊 `agent/` 目錄為何停用、新位置對照表 |
| `.kiro/steering/deploy.md` | 所有 Kiro session 自動載入的部署規則（已同步 Task 7 進度） |
| `app/careernav/main.py` | Runtime 入口，含 Task 7 新增的 `careernav_tool_result` 攔截邏輯 |
| `lambda/proxy.py` | Task 7 改寫完成，`invoke_agent_runtime` + SSE 解析 |
| `infra/lib/stack.ts` | Task 7 更新完成，`AGENT_RUNTIME_ARN` + IAM 權限，尚未部署 |
| `frontend/index.html` | Task 7 施工中（步驟 6 逐字效果未完成，步驟 7 時間軸未開始） |
