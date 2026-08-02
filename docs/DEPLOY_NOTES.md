# CareerNav 部署操作手冊

> 最後驗證：2026-08-01

## 目前部署狀態

- AWS Region：`us-west-2`
- Account：`881768789243`
- Model：`us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- AgentCore stack：`AgentCore-careernav-default`
- Runtime ID：`careernav_careernav-Su5fjSE2LM`
- Runtime 狀態：`READY`
- AgentCore invoke：已通過

## 磁碟 noexec 限制

開發 workspace：

```text
/media/data/共用文件/專案開發/aws/hoyilive
```

此磁碟以 `noexec` 掛載。npm 可以下載 `esbuild`，但作業系統拒絕執行其 binary，因此不能在 workspace 直接執行 AgentCore/CDK build。

部署副本：

```text
/home/proleader/careernav
```

| 用途 | 路徑 |
|------|------|
| 編輯、文件、Git、commit | workspace |
| npm、esbuild、CDK、AgentCore deploy | `~/careernav` |

## 安全同步

完整同步前，使用以下指令：

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

必須排除 `agentcore/.cli`，否則 `--delete` 可能移除或覆蓋部署副本中的 `deployed-state.json`。

若只修改 Runtime Agent，優先使用小範圍同步：

```bash
rsync -av app/careernav/ ~/careernav/app/careernav/
```

## 載入 AWS credentials

`.env` 使用 dotenv 格式、沒有 `export` 前綴，因此 shell 執行 CLI 前要使用 `set -a`：

```bash
cd ~/careernav
export PATH="$HOME/.local/bin:$PATH"
set -a
source .env
set +a
aws sts get-caller-identity
```

如果出現 `ExpiredToken`，重新取得 Workshop Studio credentials 並更新兩個路徑的 `.env`。

## AgentCore Runtime 部署

有效配置位於：

- `agentcore/agentcore.json`
- `agentcore/aws-targets.json`
- `agentcore/cdk/`
- `app/careernav/main.py`
- `app/careernav/pyproject.toml`

根目錄舊版 `agentcore.json` 已移除，AgentCore CLI 0.25.0 不會讀取該格式。

部署：

```bash
cd ~/careernav
export PATH="$HOME/.local/bin:$PATH"
set -a
source .env
set +a
agentcore validate
agentcore deploy --yes --verbose
```

驗證：

```bash
agentcore status --json
agentcore invoke "你好" --json
```

查 Runtime 啟動日誌：

```bash
aws logs tail \
  /aws/bedrock-agentcore/runtimes/careernav_careernav-Su5fjSE2LM-DEFAULT \
  --region us-west-2 \
  --since 10m \
  --format short
```

## 已解決的初始化錯誤

症狀：

```text
Runtime initialization time exceeded. Please make sure that initialization completes in 30s.
```

CloudWatch 根因：

```text
ImportError: cannot import name 'tool' from 'strands.types.tools'
```

修正：

```python
from strands import Agent, tool
```

修正檔案：

- `app/careernav/main.py`
- `agent/tools/career_tools.py`

修正後已重新部署並成功 invoke。

## 兩套 CDK

1. `agentcore/cdk/`：AgentCore CLI 管理，用於 Agent Runtime。
2. `infra/`：專案自有 CDK，預定用於 Lambda proxy 與 S3 前端。

AgentCore Runtime 已部署；`infra/` 尚未完成正式部署驗收，不能把目前狀態視為正式計畫 Task 6 完成。

## 後續串接注意

現有 `lambda/proxy.py` 使用傳統 Bedrock Agents 的 `bedrock-agent-runtime.invoke_agent`。目前上線的是 Bedrock AgentCore Runtime，Task 7 必須改用 AgentCore Runtime invocation API，不能只回填舊式 `AGENT_ID` / `AGENT_ALIAS_ID`。
