# 職涯導航家（CareerNav）— 專案交接文件

> 最後更新：2026-08-01
> 用途：讓新 session 直接依正式計畫接續，不重做、不跳步

## 新 session 的第一句指令

請直接使用：

> 請接續當前計畫並執行，嚴格按照 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 順序；每完成一個 Task，建立 `docs/reports/TASK_N_REPORT.md`、驗證結果並 commit。

## 一、正式進度與下一步

唯一正式計畫：`docs/IMPLEMENTATION_PLAN_20250731.md`。

| 項目 | 狀態 |
|------|------|
| Task 1：專案基礎設施設置 | 已完成，報告：`docs/reports/TASK_1_REPORT.md`，commit：`891e21a` |
| AgentCore Runtime 部署檢查點 | 已提前完成並通過 invoke；這不代表 Task 6 全部完成 |
| **下一個正式 Task** | **Task 2：實作 `resources.json` 與 `constants.json`** |
| Task 3～Task 9 | 尚未依正式計畫完成 |

不得因 Runtime 已上線而跳過 Task 2～5。Task 6 還包含基礎設施完善與完整部署驗收，目前尚未完成。

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

- `agent/`：正式實作計畫原先指定的開發目錄，Task 2、Task 3 目前仍以此為產出位置。
- `app/careernav/`：AgentCore CLI 實際打包部署的 CodeZip 目錄，目前只有可運作的骨架 Runtime。

後續 Task 2～4 必須同步處理這個落差：不要只修改 `agent/` 後就直接部署，否則 Runtime 不會包含新資料與工具。建議在 Task 4 統一成單一來源，或建立明確的打包同步步驟，並在該 Task 報告記錄決策。

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

1. **Task 2 資料尚未建立**：目前六個 Career Tools 仍是 skeleton，不能當成正式補助判斷。
2. **Lambda/S3 尚未部署**：自訂 `infra/` stack 尚未完成正式驗收。
3. **Lambda proxy API 可能不相容**：現有 `lambda/proxy.py` 使用 `bedrock-agent-runtime.invoke_agent`，但目前部署的是 AgentCore Runtime；Task 7 必須改為 AgentCore Runtime invocation API 並實測。
4. **尚未回填 Lambda 設定**：目前只有 AgentCore Runtime ID，Lambda 還未完成串接。
5. **Memory 尚未啟用**：`agentcore/agentcore.json` 現在的 `memories` 為空陣列。
6. **AWS Session Token 有效期有限**：若出現 `ExpiredToken`，更新 workspace 與 `~/careernav` 的 `.env`。
7. **Credentials 不得 commit**：`.env` 已由 `.gitignore` 排除。

## 七、下一個 session 應執行

1. 讀 `docs/IMPLEMENTATION_PLAN_20250731.md` 的 Task 2。
2. 讀 `docs/RESOURCES_SCHEMA_PROPOSAL.md`、`docs/CURRENT_DATA_ISSUES.md`、`docs/DATA_SOURCES_VERIFIED.md`。
3. 建立 `agent/data/resources.json`（15～20 筆）與 `agent/data/constants.json`。
4. 確保每筆資料具備 `law_references`、`recipient`、`source_url`、`last_verified`，金額採結構化欄位。
5. 執行資料格式與品質驗證。
6. 建立 `docs/reports/TASK_2_REPORT.md`。
7. 使用中文格式 commit，例如：`feat: 完成 Task 2 補助資料建置`。

## 八、重要文件

| 文件 | 用途 |
|------|------|
| `docs/IMPLEMENTATION_PLAN_20250731.md` | 唯一正式 Task 順序與驗收標準 |
| `docs/reports/TASK_1_REPORT.md` | Task 1 完成證據 |
| `docs/reports/AGENTCORE_RUNTIME_DEPLOYMENT_REPORT.md` | 本次 Runtime 部署檢查點 |
| `docs/DEPLOY_NOTES.md` | 雙路徑部署操作手冊 |
| `docs/RESOURCES_SCHEMA_PROPOSAL.md` | Task 2 schema 依據 |
| `docs/CURRENT_DATA_ISSUES.md` | 錯誤資料清單 |
| `docs/DATA_SOURCES_VERIFIED.md` | 已驗證資料來源 |
| `.kiro/steering/deploy.md` | 所有 Kiro session 自動載入的部署規則 |
