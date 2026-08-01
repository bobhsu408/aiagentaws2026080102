---
inclusion: auto
---

# 部署架構須知

## 正式計畫進度

- 唯一正式 Task 順序：`docs/IMPLEMENTATION_PLAN_20250731.md`
- Task 1、Task 2、**Task 3 已完成**（六步驟 Career Tools，`docs/reports/TASK_3_REPORT.md`，commit `81886fb`）。
- Task 4 的核心內容（Agent 主程式 + System Prompt）已隨 Task 3 一併完成，缺獨立報告。
- **Task 5 已完成**（MCP Client 整合 Exa AI，`docs/reports/TASK_5_REPORT.md`）。套件位於
  `app/careernav/exa_mcp/`（刻意不叫 `mcp/`，會與 PyPI 的 `mcp` 套件撞名，詳見報告）。
- **Task 6 已完成**（`docs/reports/TASK_6_REPORT.md`）：Runtime 已重新部署，**線上程式碼已是 Task 3～5 最新版**，用 `agentcore invoke` 實測六步驟工具與 Exa MCP 搜尋皆正常，CloudWatch 無錯誤。`infra/`（Lambda+S3）仍未部署。
- **Task 7（Lambda Proxy + 前端接入）施工計畫已定案**，與使用者確認過視覺風格（黑底白字標楷體、復古按鈕）、狀態機（開場動畫僅一次→首頁→對話→等待→錯誤）、時間軸視覺化規格（橫式、可點擊連結）。完整計畫見 `docs/IMPLEMENTATION_PLAN_20250731.md` Task 7 段落，新 session 直接照其「七、施工順序」執行，**不要重新詢問使用者已定案的視覺/互動細節**。第一步是技術驗證：實測 `generate_roadmap` 觸發時 SSE 事件流能否可靠抓到工具結果。
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
