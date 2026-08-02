"""Lambda Chat Proxy — 前端 HTTP → AgentCore Runtime 轉接

瀏覽器透過 Function URL 發送 POST 請求，此 Lambda 轉呼叫
Amazon Bedrock AgentCore Runtime 的 invoke_agent_runtime API，
解析 SSE 事件流組出「文字回覆」與「roadmap 結構化資料」兩份東西回給前端。

事件流格式（已透過 boto3 直接呼叫正式 Runtime 實測確認）：
    data: {"event": {"contentBlockDelta": {"delta": {"text": "..."}}}}
        → 累積 delta.text 組成完整文字回覆
    data: {"event": {"contentBlockDelta": {"delta": {"toolUse": {"input": "..."}}}}}
        → 工具呼叫的輸入參數片段（模型正在填參數），非回覆文字，忽略
    data: {"event": {"messageStart"|"messageStop"|"contentBlockStart"|"contentBlockStop": ...}}
        → 結構性事件，忽略
    data: {"careernav_tool_result": {"name": "generate_roadmap", "data": {...}}}
        → app/careernav/main.py 額外攔截 generate_roadmap 工具的原始回傳，
          直接轉發原始 JSON，不需要從文字回覆裡碎片化拼湊

環境變數：
    AGENT_RUNTIME_ARN: AgentCore Runtime ARN
    AWS_REGION_NAME: AWS Region
"""

import json
import logging
import os
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lambda timeout 為 90 秒（見 infra/lib/stack.ts），boto3 read timeout 設在其之下，
# 讓 Lambda 有餘裕在逾時前組好錯誤回應回給前端，而不是被硬中斷。
_READ_TIMEOUT_SECONDS = 75
_MIN_SESSION_ID_LEN = 33  # AgentCore runtimeSessionId 最短長度限制


def handler(event: dict, context) -> dict:
    """Lambda handler — 接收前端訊息、轉發給 AgentCore Runtime、回傳結果"""

    method = event.get("requestContext", {}).get("http", {}).get("method", "")

    # CORS preflight
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": "",
        }

    # 支援兩種帶參數方式：
    #   GET  ?q=訊息&session_id=...  ← 前端實際使用的路徑
    #   POST {"message": ..., "session_id": ...}
    #
    # 之所以以 GET 為主：本專案的公開入口是 CloudFront + Origin Access
    # Control（OAC）簽名呼叫 Lambda Function URL（AuthType=AWS_IAM），
    # 因為比賽沙盒帳號的 guardrail 會封鎖匿名（AuthType=NONE）呼叫。
    # 而 OAC 對 PUT/POST 需要「呼叫端自行計算 body 的 SHA256 並帶
    # x-amz-content-sha256 header」（Lambda 不接受 unsigned payload）；
    # 改用 GET 就沒有 body，CloudFront 可自行完成整個簽名，瀏覽器端
    # 不需做任何簽名或雜湊運算。詳見 docs/reports/TASK_7_REPORT.md。
    if method == "GET":
        params = event.get("queryStringParameters") or {}
        user_message = params.get("q", "")
        session_id = _normalize_session_id(params.get("session_id"))
    else:
        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError:
            return _response(400, {"error": "Invalid JSON body"})
        user_message = body.get("message", "")
        session_id = _normalize_session_id(body.get("session_id"))

    if not user_message:
        return _response(400, {"error": "message is required (GET: ?q=..., POST: {\"message\": ...})"})

    try:
        agent_runtime_arn = os.environ["AGENT_RUNTIME_ARN"]
    except KeyError as e:
        logger.error("Missing env var: %s", e)
        return _response(500, {"error": f"Missing env var: {e}"})

    region = os.environ.get("AWS_REGION_NAME", "us-west-2")
    client = boto3.client(
        "bedrock-agentcore",
        region_name=region,
        config=Config(read_timeout=_READ_TIMEOUT_SECONDS, connect_timeout=10),
    )

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_runtime_arn,
            runtimeSessionId=session_id,
            payload=json.dumps({"prompt": user_message}).encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )
        raw_stream = response["response"].read()
    except (BotoCoreError, ClientError) as e:
        logger.exception("AgentCore invoke_agent_runtime failed")
        return _response(502, {
            "error": "無法連上 AI 服務，請稍後再試",
            "details": str(e),
            "session_id": session_id,
        })
    except Exception as e:
        logger.exception("Unexpected error calling AgentCore")
        return _response(500, {
            "error": "發生未預期的錯誤",
            "details": str(e),
            "session_id": session_id,
        })

    reply_text, roadmap = _parse_sse_stream(raw_stream)

    if not reply_text and roadmap is None:
        # 串流解析不出任何內容，視為異常但不讓前端卡住等待動畫。
        logger.error("Empty reply parsed from AgentCore stream, raw length=%d", len(raw_stream))
        return _response(502, {
            "error": "AI 服務回應為空，請重新嘗試",
            "session_id": session_id,
        })

    return _response(200, {
        "reply": reply_text,
        "session_id": session_id,
        "roadmap": roadmap,
    })


def _normalize_session_id(session_id) -> str:
    """確保 session_id 符合 AgentCore runtimeSessionId 長度限制（33~256 字元）。"""
    if not session_id or not isinstance(session_id, str):
        return str(uuid.uuid4())
    if len(session_id) < _MIN_SESSION_ID_LEN:
        # 前端若傳入過短的 id，補齊長度而非直接拋錯，避免中斷對話流程。
        return (session_id + "-" + uuid.uuid4().hex)[:64]
    return session_id[:256]


def _parse_sse_stream(raw: bytes) -> tuple[str, dict | None]:
    """解析 AgentCore SSE 事件流，組出文字回覆與 roadmap 結構化資料。

    Args:
        raw: invoke_agent_runtime 回應串流讀出的原始 bytes

    Returns:
        (reply_text, roadmap)：roadmap 若這輪沒呼叫 generate_roadmap 則為 None
    """
    text_parts: list[str] = []
    roadmap: dict | None = None

    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload_str = line[len("data:"):].strip()
        if not payload_str:
            continue

        try:
            obj = json.loads(payload_str)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed SSE line: %s", payload_str[:200])
            continue

        # 自訂事件：generate_roadmap 的原始回傳（main.py 額外轉發，見模組 docstring）。
        tool_result = obj.get("careernav_tool_result")
        if isinstance(tool_result, dict) and tool_result.get("name") == "generate_roadmap":
            data = tool_result.get("data")
            if isinstance(data, dict):
                roadmap = data
            continue

        # 一般模型串流事件：只取文字 delta，忽略工具輸入參數 delta 與結構性事件。
        inner_event = obj.get("event")
        if not isinstance(inner_event, dict):
            continue
        delta = inner_event.get("contentBlockDelta", {}).get("delta", {})
        text = delta.get("text")
        if isinstance(text, str):
            text_parts.append(text)

    return "".join(text_parts), roadmap


def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
    }


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            **_cors_headers(),
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
