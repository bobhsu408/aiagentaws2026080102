#!/usr/bin/env bash
# 部署腳本 — AgentCore + CDK
# 使用方式：bash scripts/deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== 1. CDK 部署基礎設施 ==="
cd "$PROJECT_ROOT/infra"
npm install
npx cdk deploy --require-approval never

echo ""
echo "=== 2. AgentCore 部署 Agent ==="
cd "$PROJECT_ROOT"
agentcore deploy

echo ""
echo "=== 部署完成 ==="
echo "請確認以下輸出值，並更新 Lambda 環境變數中的 AGENT_ID / AGENT_ALIAS_ID"
