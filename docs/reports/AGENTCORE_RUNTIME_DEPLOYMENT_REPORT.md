# AgentCore Runtime 部署檢查點報告

> 日期：2026-08-01
> 性質：比賽期間提前驗證部署鏈路
> 注意：本報告不代表正式計畫 Task 6 已全部完成

## 目的

在進入 Task 2～5 前，先確認 AWS credentials、Bedrock 模型、AgentCore CLI、CDK 與 CodeZip Runtime 可正常部署與呼叫，降低後續整合風險。

## AWS 環境

- Region：`us-west-2`
- Account：`881768789243`
- Model：`us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- AgentCore CLI：`0.25.0`
- AWS CDK CLI：`2.1134.0`
- Node.js：`v22.22.1`

## 完成項目

1. 確認 Claude Sonnet 4.5 foundation model 與 US inference profile 可用。
2. 建立 AgentCore CLI 0.25.0 所需結構：
   - `agentcore/agentcore.json`
   - `agentcore/aws-targets.json`
   - `agentcore/cdk/`
   - `app/careernav/main.py`
   - `app/careernav/pyproject.toml`
3. 以 CodeZip / Python 3.14 部署 AgentCore Runtime。
4. 排除 workspace `noexec` 問題，建立 `~/careernav` 部署副本。
5. 修正 Strands `tool` import 相容性問題。
6. 重新部署既有 Runtime。
7. 使用 `agentcore invoke` 成功取得繁體中文回覆。
8. 檢查最近驗證時段 CloudWatch，沒有新的 ERROR、Traceback、ImportError 或 Exception。

## 部署結果

| 項目 | 值 |
|------|----|
| Stack | `AgentCore-careernav-default` |
| Runtime ID | `careernav_careernav-Su5fjSE2LM` |
| Runtime ARN | `arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM` |
| Runtime 狀態 | `READY` |
| Invoke | 成功 |

## 問題與修正

### 1. esbuild 無法執行

症狀：`spawnSync .../esbuild EACCES`。

根因：workspace 所在 `/media/data` 檔案系統以 `noexec` 掛載，與中文路徑無關。

解法：在 workspace 開發與 commit，部署前同步至 `~/careernav`，從可執行的 home filesystem 執行 npm/CDK/AgentCore。

### 2. Runtime initialization timeout

表面錯誤：

```text
Runtime initialization time exceeded
```

CloudWatch 真正錯誤：

```text
ImportError: cannot import name 'tool' from 'strands.types.tools'
```

修正：

```python
from strands import Agent, tool
```

套用於：

- `app/careernav/main.py`
- `agent/tools/career_tools.py`

## 驗證證據

實際 invoke 測試輸入：

```text
你好，我是35歲的餐廳主管，剛被裁員，請先告訴我你需要哪些資料才能判斷補助資格。
```

結果：CLI 回傳 `success: true`，Agent 以繁體中文詢問就業保險年資、投保薪資、非自願離職證明、扶養家屬、職訓意願與特殊身分。

## 尚未完成

- Task 2 的正式補助資料與 constants 尚未建立。
- 六個 Career Tools 仍為 skeleton。
- `infra/` 的 Lambda + S3 尚未完成部署驗收。
- Lambda 尚未改用 AgentCore Runtime invocation API。
- 前端尚未完成端到端串接。
- AgentCore Memory 尚未啟用。

## 正式計畫下一步

回到 `docs/IMPLEMENTATION_PLAN_20250731.md`，從 **Task 2** 開始。完成後建立 `docs/reports/TASK_2_REPORT.md` 並 commit，不得直接將此部署檢查點視為 Task 6 完成。
