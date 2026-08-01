#!/usr/bin/env bash
# 權限檢查腳本 — 比賽拿到新帳號後快速確認可用服務
# 使用方式：bash scripts/check_permissions.sh

set -uo pipefail

echo "=== AWS 帳號確認 ==="
aws sts get-caller-identity

echo ""
echo "=== Bedrock 模型存取 ==="
aws bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `claude`)].modelId' --output table 2>/dev/null && echo "✓ Bedrock OK" || echo "✗ Bedrock FAILED"

echo ""
echo "=== Lambda ==="
aws lambda list-functions --region us-west-2 --query 'Functions[0].FunctionName' 2>/dev/null && echo "✓ Lambda OK" || echo "✗ Lambda FAILED"

echo ""
echo "=== S3 ==="
aws s3 ls 2>/dev/null && echo "✓ S3 OK" || echo "✗ S3 FAILED"

echo ""
echo "=== Cognito ==="
aws cognito-idp list-user-pools --max-results 1 --region us-west-2 2>/dev/null && echo "✓ Cognito OK" || echo "✗ Cognito FAILED"

echo ""
echo "=== IAM (read-only check) ==="
aws iam get-user 2>/dev/null && echo "✓ IAM OK" || aws iam list-roles --max-items 1 2>/dev/null && echo "✓ IAM (role) OK" || echo "✗ IAM FAILED"

echo ""
echo "=== AgentCore ==="
which agentcore 2>/dev/null && agentcore --version && echo "✓ AgentCore CLI OK" || echo "⚠ AgentCore CLI not found"
