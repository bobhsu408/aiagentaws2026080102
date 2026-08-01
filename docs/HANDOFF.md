# 職涯導航家（CareerNav）— 專案交接文件

> 最後更新：2026-08-01（Task 3 完成後收尾）
> 用途：讓新 session 直接依正式計畫接續，不重做、不跳步、不用重讀大量歷史文件

## 新 session 的第一句指令

請直接使用：

> 請接續當前計畫並執行，嚴格按照 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 順序；每完成一個 Task，建立 `docs/reports/TASK_N_REPORT.md`、驗證結果並 commit。

## 一、正式進度與下一步

唯一正式計畫：`docs/IMPLEMENTATION_PLAN_20250731.md`。

| 項目 | 狀態 |
|------|------|
| Task 1：專案基礎設施設置 | 已完成，報告：`docs/reports/TASK_1_REPORT.md`，commit：`891e21a` |
| AgentCore Runtime 部署檢查點 | 已提前完成並通過 invoke；這不代表 Task 6 全部完成 |
| Task 2：實作 `resources.json` 與 `constants.json` | 已完成（MVP 範圍，見下方說明），報告：`docs/reports/TASK_2_REPORT.md` |
| Task 3：實作六步驟 Career Tools | **已完成**，報告：`docs/reports/TASK_3_REPORT.md`，commit：`81886fb` |
| Task 4：Agent 主程式與 System Prompt | **副產品已完成**，見下方「Task 3 順帶完成的部分」，尚無獨立報告 |
| **下一個建議 Task** | **Task 5：MCP Client 整合（Exa AI）**，或先補一份 Task 4 確認報告後再進 Task 5 |
| Task 6～Task 9 | 尚未依正式計畫完成 |

不得因 Runtime 已上線而跳過 Task 5。Task 6 還包含基礎設施完善與完整部署驗收，目前尚未完成，且**目前的程式碼變更尚未重新部署**（見第五節）。

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

預定端到端架構（尚未完成）
瀏覽器 → Lambda proxy → AgentCore Runtime → Strands Agent → Career Tools
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

1. **Runtime 尚未重新部署新程式碼**：Task 3 的六步驟工具與資料只存在於 workspace，**AgentCore Runtime 上跑的還是舊骨架**（inline 空殼工具）。要讓 demo 反映最新邏輯，必須先跑一次部署流程（見第五節 `docs/DEPLOY_NOTES.md`），屬 Task 6 範圍或先行驗證用。
2. **Lambda/S3 尚未部署**：自訂 `infra/` stack 尚未完成正式驗收。
3. **Lambda proxy API 可能不相容**：現有 `lambda/proxy.py` 使用 `bedrock-agent-runtime.invoke_agent`，但目前部署的是 AgentCore Runtime；Task 7 必須改為 AgentCore Runtime invocation API 並實測。
4. **尚未回填 Lambda 設定**：目前只有 AgentCore Runtime ID，Lambda 還未完成串接。
5. **Memory 尚未啟用**：`agentcore/agentcore.json` 現在的 `memories` 為空陣列。
6. **AWS Session Token 有效期有限**：若出現 `ExpiredToken`，更新 workspace 與 `~/careernav` 的 `.env`。
7. **Credentials 不得 commit**：`.env` 已由 `.gitignore` 排除。
8. **資料範圍僅涵蓋情境 A**：情境 B（雇主僱用中高齡）、情境 C（高齡者+代理人操作）尚無對應 `resources.json` 資料，Task 8 端到端測試前需決定是否補齊。
9. **課程資料僅 3 筆計畫層級樣本**：`app/careernav/data/courses.json` 是穩定資訊，即時開課梯次要等 Task 5 接上 Exa MCP 才能補（`generate_roadmap` 已預留 `course_hint`／`hint.keywords` 欄位供即時搜尋使用）。
10. **LINE 通知尚未啟用**：`send_notification` 目前為展示用 email 純模擬（`channel: "email"`, `demo_mode: true`）。介面已預留 `line_user_id` 參數；待取得 LINE Channel Access Token 後可加真推播＋自動降級模擬（`.env.example` 已加 `LINE_CHANNEL_ACCESS_TOKEN`／`LINE_DEMO_USER_ID` 欄位待填）。
11. **`agent/` 目錄已停用**：不要再修改或讀取 `agent/` 下的程式碼與資料，一律在 `app/careernav/` 操作（見 `agent/DEPRECATED.md`）。

## 七、下一個 session 應執行

**若要驗證目前的六步驟工具邏輯**（不需要重讀大量文件）：
```bash
cd app/careernav
~/careernav_venv/bin/python -m pytest tests/ -q   # 若無此 venv，見下方建立指令
```
建立測試 venv（若尚未建立）：
```bash
python3 -m venv ~/careernav_venv
~/careernav_venv/bin/pip install --quiet pytest strands-agents
```

**下一步建議走 Task 5（MCP Client 整合 Exa AI）**：
1. 讀 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 5 段落。
2. 在 `app/careernav/mcp/` 建立 MCP Client 封裝（`agent/mcp/__init__.py` 只是空殼佔位，記得同樣要在 `app/careernav/` 下建立，不要延用 `agent/`）。
3. 介面需求：輸入 query（可用 `generate_roadmap` 回傳的 `courses.hint.keywords`）、輸出搜尋結果、加 timeout + graceful degradation（搜尋失敗不能讓整個 Agent 掛掉）。
4. 在 `app/careernav/main.py` 的 Agent 建構處註冊 MCP tools。
5. 建立 `docs/reports/TASK_5_REPORT.md`，中文 commit。

**若想先補 Task 4 的正式報告**（Task 3 已順帶完成其內容，見第一節）：
1. 讀 `app/careernav/main.py` 目前的 `SYSTEM_PROMPT` 與 `agent_factory()`，確認是否要調整人設或追問邏輯。
2. 若無異議，直接寫 `docs/reports/TASK_4_REPORT.md` 引用 Task 3 的變更即可，不必重新設計。

**若要讓 demo 真的跑起來**：需先執行 `docs/DEPLOY_NOTES.md` 的部署流程，把 `app/careernav/` 同步到 `~/careernav` 並重新 `agentcore deploy`。

## 八、重要文件

| 文件 | 用途 |
|------|------|
| `docs/IMPLEMENTATION_PLAN_20250731.md` | 唯一正式 Task 順序與驗收標準（含子代理平行策略） |
| `docs/reports/TASK_1_REPORT.md` | Task 1 完成證據 |
| `docs/reports/TASK_2_REPORT.md` | Task 2 完成證據（含情境 A 範圍調整說明） |
| `docs/reports/TASK_3_REPORT.md` | Task 3 完成證據（六步驟工具設計決策、測試結果） |
| `docs/reports/AGENTCORE_RUNTIME_DEPLOYMENT_REPORT.md` | 本次 Runtime 部署檢查點 |
| `docs/DEPLOY_NOTES.md` | 雙路徑部署操作手冊 |
| `docs/RESOURCES_SCHEMA_PROPOSAL.md` | Task 2 schema 依據 |
| `docs/CURRENT_DATA_ISSUES.md` | 錯誤資料清單 |
| `docs/DATA_SOURCES_VERIFIED.md` | 已驗證資料來源 |
| `agent/DEPRECATED.md` | 說明舊 `agent/` 目錄為何停用、新位置對照表 |
| `.kiro/steering/deploy.md` | 所有 Kiro session 自動載入的部署規則 |
