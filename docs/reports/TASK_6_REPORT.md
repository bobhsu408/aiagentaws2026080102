# Task 6 完成報告 — CDK 基礎設施完善 + AgentCore 部署

> 完成日期：2026-08-01
> 對應計畫：`docs/IMPLEMENTATION_PLAN_20250731.md` Task 6
> 前置：Task 3（六步驟 Career Tools）、Task 5（MCP Client）

---

## 一、目標

把 Task 3～5 的新程式碼（六步驟工具、Exa MCP client）重新打包並用
`agentcore deploy` 部署到 AWS，取代線上仍在跑的舊骨架版本；驗證 Runtime
狀態、實際 invoke 回覆內容、CloudWatch 無錯誤。

---

## 二、部署前檢查

### 2.1 上次部署失敗原因

`agentcore/.cli/logs/deploy/deploy-20260801-171020.log` 記錄了上次部署
在 `Sync CDK dependencies` 階段失敗：

```
npm ERR! Error: spawnSync .../node_modules/esbuild/bin/esbuild EACCES
```

根因：該次部署指令在 workspace（`/media/data/...`，`noexec` 掛載磁碟）
下執行，esbuild binary 無法被系統允許執行。這正是 `docs/DEPLOY_NOTES.md`
記載過的雙路徑限制——必須在 `~/careernav`（可執行的 home filesystem）
執行 npm/CDK/AgentCore 相關指令。

### 2.2 本次修正

1. 確認 AWS credentials 有效：`aws sts get-caller-identity` 成功回應
   `Account: 881768789243`（Workshop Studio Participant role）。
2. 用安全同步指令把 workspace 最新程式碼（含 Task 3～5、Exa MCP）同步到
   `~/careernav`：
   ```bash
   rsync -av --delete \
     --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
     --exclude='.pytest_cache' --exclude='cdk.out' --exclude='agentcore/.cli' \
     "/media/data/共用文件/專案開發/aws/hoyilive/" "$HOME/careernav/"
   ```
   同步結果確認 `app/careernav/exa_mcp/`、`tests/test_exa_mcp_client.py`、
   `pytest.ini` 等 Task 5 新檔案都已進入 `~/careernav`。
3. 過程中發現並清除一個殘留的空 `app/careernav/mcp/` 資料夾（Task 5
   設計初版誤建、後刪除檔案但資料夾殘留），確認清除後不影響命名衝突
   風險（詳見 `docs/reports/TASK_5_REPORT.md` 決策 D1）。
4. 確認 `~/careernav/agentcore/cdk/node_modules/esbuild` 在 home
   filesystem 上可正常執行（`esbuild --version` → `0.28.1`）。

---

## 三、部署執行

於 `~/careernav` 執行（**不是** workspace）：

```bash
export PATH="$HOME/.local/bin:$PATH"
set -a; source .env; set +a
agentcore validate   # → Valid
agentcore deploy --yes --verbose
```

部署結果：

| 項目 | 值 |
|------|----|
| Stack | `AgentCore-careernav-default` |
| 操作類型 | `UPDATE`（非新建，Runtime ID 沿用既有） |
| Runtime ID | `careernav_careernav-Su5fjSE2LM` |
| Runtime ARN | `arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM` |
| CloudFormation 結果 | `UPDATE_COMPLETE`（3/3 資源） |
| 部署耗時 | 約 3 分鐘（`23:13:24` 開始 → `23:14:16` Stack 完成） |

`agentcore status --json` 確認：
```json
{
  "success": true,
  "resources": [{
    "resourceType": "agent",
    "name": "careernav",
    "deploymentState": "deployed",
    "detail": "READY"
  }]
}
```

---

## 四、Invoke 驗證

### 4.1 案例一：情境 A 六步驟工具

輸入：
```
你好，我58歲，在工廠工作上個月被資遣，就保保了20年，請問我可以申請哪些補助？
```

回覆重點（節錄）：
- 正確識別 45 歲以上失業給付延長為 **9 個月**（一般為 6 個月）
- 明確提示失業給付與職業訓練生活津貼**不得同時領取，需擇一**
- 列出 6 項符合資格方案（失業給付、職訓生活津貼、提早就業獎助、異地就業
  交通/搬遷/租屋補助）
- 缺投保薪資時以基本工資 29,500 元做保守估算並註明是估算值
- 提及眷屬加給 10%/人上限 20%

CloudWatch 記錄實際呼叫順序：`Tool #1: analyze_profile` →
`Tool #2: match_resources` → `Tool #3: calculate_benefit`，與 Task 3
設計的六步驟流程一致，證明**新程式碼確實已上線**，非舊骨架空殼工具。

### 4.2 案例二：Exa MCP 即時搜尋（驗證 Task 5 整合）

輸入：
```
請幫我查一下最近有什麼中高齡職業訓練課程正在招生
```

回覆包含具體課程名稱（CNC數控班、生成式AI與全端程式設計班等）、開課時間、
官方查詢網址（`https://course.taiwanjobs.gov.tw`、
`https://45plus.wda.gov.tw`）——這些內容**不在**靜態 `courses.json`
資料中，證明回覆確實來自即時網路搜尋而非套用固定資料。

CloudWatch 記錄：
```
Tool #1: web_search_exa
Tool #2: web_search_exa
```

確認 `web_search_exa` 被 Agent 實際呼叫兩次，且**無任何** ERROR、
Exception、Traceback。

### 4.3 CloudWatch 整體檢查

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/careernav_careernav-Su5fjSE2LM-DEFAULT \
  --region us-west-2 --since 20m --format short \
  | grep -iE "error|traceback|exception|importerror|timeout|fail"
# 無輸出
```

兩次 invoke 的初始化到首個回應皆在 1 秒內完成（無
`Runtime initialization time exceeded`），確認 Task 5 新增的
`exa_mcp/` 套件命名（避開與 PyPI `mcp` 套件衝突）在實際 Runtime 環境下
沒有造成 import 問題。

---

## 五、已知限制與未完成事項

1. **`infra/` 尚未部署**：本 Task 完成的是 `agentcore/cdk/`（AgentCore
   Runtime 本身）。專案自有的 `infra/lib/stack.ts`（Lambda proxy + S3
   前端）仍未部署驗收，屬 Task 7 範圍。
2. **AgentCore Memory 未啟用**：`agentcore/agentcore.json` 的
   `memories` 仍為空陣列，非本次 Task 範圍。
3. **Exa API key 未設定**：`.env` 中 `EXA_API_KEY` 為空，目前以 keyless
   模式運作（有速率限制）。本次兩次搜尋測試皆成功，demo 前應留意若
   密集測試可能觸發 429，Agent 會依 System Prompt 指示優雅跳過。
4. **Lambda proxy 仍待改寫**：`lambda/proxy.py` 目前呼叫舊式
   `bedrock-agent-runtime.invoke_agent`，非本次部署的 AgentCore Runtime
   invocation API，Task 7 必須修正。
5. **前端尚未串接**：`frontend/index.html` 尚未與此 Runtime 對接。

---

## 六、下一步

依 `docs/IMPLEMENTATION_PLAN_20250731.md`，下一個 Task 是 **Task 7：
Lambda Proxy + 前端接入**（讓瀏覽器能透過 HTTP 跟 Agent 對話）。
使用者已提出前端應在等待回覆／搜尋時顯示載入動畫，屬該 Task 的 UI 需求
之一（見 `docs/reports/TASK_5_REPORT.md` 第六節）。
