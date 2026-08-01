---
inclusion: auto
---

# 部署架構須知

## 正式計畫進度

- 唯一正式 Task 順序：`docs/IMPLEMENTATION_PLAN_20250731.md`
- Task 1、Task 2、**Task 3 已完成**（六步驟 Career Tools，`docs/reports/TASK_3_REPORT.md`，commit `81886fb`）。
- Task 4 的核心內容（Agent 主程式 + System Prompt）已隨 Task 3 一併完成，缺獨立報告。
- AgentCore Runtime 已提前部署並成功 invoke，但那是**舊骨架版本**，尚未包含 Task 3 的新程式碼；這只是檢查點，不代表 Task 6 完成。
- 新 session 下一步建議從 **Task 5（MCP Client / Exa AI）** 開始，或先補一份 Task 4 報告；每完成一個 Task 要建立報告並 commit。
- 詳細現況與待辦：`docs/HANDOFF.md`（每次 Task 完成後應同步更新此檔案）。

## AWS Runtime

- Region：`us-west-2`
- Model：`us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Account：`881768789243`
- Stack：`AgentCore-careernav-default`
- Runtime ID：`careernav_careernav-Su5fjSE2LM`
- Runtime 狀態：`READY`
- Credentials：`.env`，Session Token 有效期有限，不得 commit

## 磁碟限制與雙路徑

Workspace `/media/data/共用文件/專案開發/aws/hoyilive` 位於 `noexec` 磁碟，不能執行 esbuild 等 binary。

- 開發、文件、Git：workspace
- npm、CDK、AgentCore deploy：`~/careernav`

安全同步：

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

不得覆蓋 `~/careernav/agentcore/.cli/deployed-state.json`。

## 部署指令

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

## AgentCore CLI 結構

- `agentcore/agentcore.json`：有效 CLI 配置
- `app/careernav/main.py`：BedrockAgentCoreApp 入口，載入 `tools.career_tools.TOOL_REGISTRY`
- `app/careernav/tools/`：六步驟工具（`logic.py` 純邏輯 + `career_tools.py` @tool 封裝 + 支援模組）
- `app/careernav/data/`：`resources.json` / `constants.json` / `courses.json`
- `app/careernav/tests/`：單元測試（15 個，`~/careernav_venv/bin/python -m pytest tests/ -q`）
- `app/careernav/pyproject.toml`：CodeZip 依賴
- `agentcore/cdk/`：AgentCore CLI 管理的 CDK
- 根目錄舊版 `agentcore.json` 已移除，不能使用

## 兩套 CDK

1. `agentcore/cdk/`：Agent Runtime，已部署。
2. `infra/`：Lambda proxy + S3，尚未完成部署驗收。

## 已知整合風險

- `agent/` 已於 Task 3 標記 **DEPRECATED**（見 `agent/DEPRECATED.md`），不得再修改。唯一真實來源是 `app/careernav/`。
- **Runtime 尚未重新部署 Task 3 的新程式碼**：目前線上跑的還是舊骨架版本。要讓 demo 反映最新六步驟邏輯，需先跑一次本節「部署指令」。
- `lambda/proxy.py` 目前呼叫傳統 Bedrock Agents API，不是 AgentCore Runtime API；Task 7 必須修正並實測。
- Strands 的 `tool` 必須由頂層匯入：`from strands import tool`。

完整操作：`docs/DEPLOY_NOTES.md`；最新交接：`docs/HANDOFF.md`。
