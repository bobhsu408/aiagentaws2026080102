# 職涯導航家（CareerNav）— 專案交接文件

> 最後更新：2026-08-01
> 用途：讓新 session 直接依正式計畫接續，不重做、不跳步

## 新 session 的第一句指令

請直接使用：

> 請接續當前計畫並執行，嚴格按照 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 順序；每完成一個 Task，建立 `docs/reports/TASK_N_REPORT.md`、驗證結果並 commit。

## 一、正式進度與下一步

唯一正式計畫：`docs/IMPLEMENTATION_PLAN_20250731.md`（已於本次 session 改寫，加入子代理平行執行策略、Wave 圖、子代理使用守則）。

| 項目 | 狀態 |
|------|------|
| Task 1：專案基礎設施設置 | 已完成，報告：`docs/reports/TASK_1_REPORT.md`，commit：`891e21a` |
| AgentCore Runtime 部署檢查點 | 已提前完成並通過 invoke；這不代表 Task 6 全部完成 |
| Task 2：實作 `resources.json` 與 `constants.json` | 已完成（MVP 範圍，見下方說明），報告：`docs/reports/TASK_2_REPORT.md` |
| **下一個正式 Task** | **Task 3：實作六步驟 Career Tools**（讓 `match_resources`/`calculate_benefit` 改讀新 schema） |
| Task 4～Task 9 | 尚未依正式計畫完成 |

不得因 Runtime 已上線而跳過 Task 3～5。Task 6 還包含基礎設施完善與完整部署驗收，目前尚未完成。

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
       └── CodeZip: app/careernav/
            ├── main.py              # BedrockAgentCoreApp Runtime 入口
            └── pyproject.toml       # Runtime 依賴

預定端到端架構（尚未完成）
瀏覽器 → Lambda proxy → AgentCore Runtime → Strands Agent → Career Tools
```

### 兩套 Agent 程式碼的現況

- `agent/`：正式實作計畫原先指定的開發目錄。Task 2 的 `resources.json`／`constants.json` 已在此建立；Task 3 目前仍以此為產出位置。
- `app/careernav/`：AgentCore CLI 實際打包部署的 CodeZip 目錄，目前只有可運作的骨架 Runtime，**尚未包含 Task 2 的資料**。

後續 Task 3～4 必須同步處理這個落差：不要只修改 `agent/` 後就直接部署，否則 Runtime 不會包含新資料與工具。建議在 Task 4 統一成單一來源，或建立明確的打包同步步驟，並在該 Task 報告記錄決策。

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

1. **Career Tools 仍是 skeleton，尚未讀取 Task 2 資料**：`agent/data/resources.json`／`constants.json` 已存在（情境 A，6 筆），但 `agent/tools/career_tools.py` 的 `match_resources`／`calculate_benefit` 還沒改寫成讀取新 schema，這是 Task 3 的工作，不能跳過。
2. **Lambda/S3 尚未部署**：自訂 `infra/` stack 尚未完成正式驗收。
3. **Lambda proxy API 可能不相容**：現有 `lambda/proxy.py` 使用 `bedrock-agent-runtime.invoke_agent`，但目前部署的是 AgentCore Runtime；Task 7 必須改為 AgentCore Runtime invocation API 並實測。
4. **尚未回填 Lambda 設定**：目前只有 AgentCore Runtime ID，Lambda 還未完成串接。
5. **Memory 尚未啟用**：`agentcore/agentcore.json` 現在的 `memories` 為空陣列。
6. **AWS Session Token 有效期有限**：若出現 `ExpiredToken`，更新 workspace 與 `~/careernav` 的 `.env`。
7. **Credentials 不得 commit**：`.env` 已由 `.gitignore` 排除。
8. **資料範圍僅涵蓋情境 A**：情境 B（雇主僱用中高齡）、情境 C（高齡者+代理人操作）尚無對應 `resources.json` 資料，Task 8 端到端測試前需決定是否補齊。

## 七、下一個 session 應執行

1. 讀 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 3。
2. 讀 `agent/data/resources.json`（情境 A 的 6 筆資料）與 `docs/RESOURCES_SCHEMA_PROPOSAL.md`（schema 定義）。
3. 改寫 `agent/tools/career_tools.py` 的 `match_resources`／`calculate_benefit`，讓其讀取新 schema 的 `benefit.base`/`conditional_tiers`/`surcharges`/`concurrency_rules`，而非舊版骨架的空殼回傳。
4. 若要擴充情境 B（雇主僱用中高齡）或情境 C（高齡者+代理人操作）的資料，可先用 Task 2 的子代理平行策略查證，再補進 `resources.json`（注意 `id` 不可與現有 6 筆衝突）。
5. 執行單元測試或至少手動呼叫每個 tool 驗證回傳合理。
6. 建立 `docs/reports/TASK_3_REPORT.md`。
7. 使用中文格式 commit，例如：`feat: 完成 Task 3 六步驟 Career Tools`。

## 八、重要文件

| 文件 | 用途 |
|------|------|
| `docs/IMPLEMENTATION_PLAN_20250731.md` | 唯一正式 Task 順序與驗收標準（含子代理平行策略） |
| `docs/reports/TASK_1_REPORT.md` | Task 1 完成證據 |
| `docs/reports/TASK_2_REPORT.md` | Task 2 完成證據（含情境 A 範圍調整說明） |
| `docs/reports/AGENTCORE_RUNTIME_DEPLOYMENT_REPORT.md` | 本次 Runtime 部署檢查點 |
| `docs/DEPLOY_NOTES.md` | 雙路徑部署操作手冊 |
| `docs/RESOURCES_SCHEMA_PROPOSAL.md` | Task 2 schema 依據 |
| `docs/CURRENT_DATA_ISSUES.md` | 錯誤資料清單 |
| `docs/DATA_SOURCES_VERIFIED.md` | 已驗證資料來源 |
| `.kiro/steering/deploy.md` | 所有 Kiro session 自動載入的部署規則 |
