"""LINE Messaging API Webhook — LINE → AgentCore Runtime 轉接

LINE 使用者傳訊息 → LINE Platform POST 到此 Lambda → 呼叫 AgentCore
→ 拿到回覆 → 用 LINE Reply API 回傳給使用者。

架構：
    LINE App → LINE Platform (Webhook) → 此 Lambda → AgentCore Runtime → Agent
    LINE App ← LINE Platform (Reply API) ← 此 Lambda ←─────────────────────────

環境變數：
    LINE_CHANNEL_SECRET: LINE Channel Secret（驗證簽名用）
    LINE_CHANNEL_ACCESS_TOKEN: LINE Channel Access Token（回覆用）
    AGENT_RUNTIME_ARN: AgentCore Runtime ARN
    AWS_REGION_NAME: AWS Region
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import uuid
import urllib.request

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_READ_TIMEOUT_SECONDS = 75
_MIN_SESSION_ID_LEN = 33

# LINE 單則訊息上限
_LINE_TEXT_MAX_LEN = 5000
# LINE 一次最多回覆幾則訊息
_LINE_MAX_MESSAGES = 5


def handler(event: dict, context) -> dict:
    """Lambda handler — 接收 LINE Webhook 事件並轉發給 AgentCore Runtime"""

    body = event.get("body", "")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    # 驗證 LINE 簽名
    channel_secret = os.environ.get("LINE_CHANNEL_SECRET", "")
    signature = headers.get("x-line-signature", "")

    if not _verify_signature(body, channel_secret, signature):
        logger.warning("Invalid LINE signature")
        return {"statusCode": 403, "body": "Invalid signature"}

    # 解析 Webhook 事件
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": "Invalid JSON"}

    events = body_json.get("events", [])

    for evt in events:
        # 只處理文字訊息事件
        if evt.get("type") != "message":
            continue
        if evt.get("message", {}).get("type") != "text":
            continue

        user_message = evt["message"]["text"].strip()
        reply_token = evt["replyToken"]
        user_id = evt["source"]["userId"]

        if not user_message:
            continue

        # 用 LINE userId 當 session id（讓同一用戶的對話有連續性）
        session_id = _build_session_id(user_id)

        # 呼叫 AgentCore Runtime 取得回覆
        try:
            reply_text = _invoke_agent(user_message, session_id)
        except Exception as e:
            logger.exception("AgentCore invocation failed for user %s", user_id)
            reply_text = "抱歉，系統目前暫時忙碌中，請稍後再試一次 🙏"

        # 用 Reply API 回覆使用者
        _reply_line(reply_token, reply_text)

    # LINE Platform 要求回傳 200
    return {"statusCode": 200, "body": "OK"}


# ============================================================================
# 內部函式
# ============================================================================


def _verify_signature(body: str, channel_secret: str, signature: str) -> bool:
    """驗證 LINE Webhook 的 X-Line-Signature。

    Args:
        body: 原始 request body 字串
        channel_secret: LINE Channel Secret
        signature: 來自 header 的簽名值

    Returns:
        簽名是否合法
    """
    if not channel_secret or not signature:
        # 若未設定 secret，開發環境下跳過驗證（正式部署務必設定）
        logger.warning("LINE_CHANNEL_SECRET not set, skipping signature verification")
        return True

    hash_val = hmac.new(
        channel_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(hash_val).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _build_session_id(user_id: str) -> str:
    """用 LINE userId 組出符合 AgentCore 長度要求的 session id。

    Args:
        user_id: LINE userId（通常為 U 開頭 33 字元）

    Returns:
        長度 >= 33 的 session id 字串
    """
    session_id = f"line-{user_id}"
    if len(session_id) < _MIN_SESSION_ID_LEN:
        session_id = (session_id + "-" + uuid.uuid4().hex)[:64]
    return session_id


def _invoke_agent(user_message: str, session_id: str) -> str:
    """呼叫 AgentCore Runtime，回傳純文字回覆。

    Args:
        user_message: 使用者傳來的文字
        session_id: 對話 session ID

    Returns:
        Agent 回覆的文字內容
    """
    region = os.environ.get("AWS_REGION_NAME", "us-west-2")
    agent_runtime_arn = os.environ["AGENT_RUNTIME_ARN"]

    client = boto3.client(
        "bedrock-agentcore",
        region_name=region,
        config=Config(read_timeout=_READ_TIMEOUT_SECONDS, connect_timeout=10),
    )

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": user_message}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    raw_stream = response["response"].read()

    # 解析 SSE 串流（與 proxy.py 同邏輯）
    text_parts: list[str] = []
    for line in raw_stream.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload_str = line[len("data:"):].strip()
        if not payload_str:
            continue
        try:
            obj = json.loads(payload_str)
        except json.JSONDecodeError:
            continue

        inner_event = obj.get("event")
        if not isinstance(inner_event, dict):
            continue
        delta = inner_event.get("contentBlockDelta", {}).get("delta", {})
        text = delta.get("text")
        if isinstance(text, str):
            text_parts.append(text)

    reply = "".join(text_parts)
    return reply if reply else "抱歉，目前無法處理您的訊息，請稍後再試 🙏"


def _reply_line(reply_token: str, text: str) -> None:
    """用 LINE Reply API 回覆訊息。

    若文字超過 5000 字會自動分段（最多 5 則）。

    Args:
        reply_token: LINE 回覆 token
        text: 要回覆的文字
    """
    access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not access_token:
        logger.error("LINE_CHANNEL_ACCESS_TOKEN not set, cannot reply")
        return

    url = "https://api.line.me/v2/bot/message/reply"

    # 分段處理：每段最多 5000 字，最多 5 則
    messages: list[dict] = []
    for i in range(0, len(text), _LINE_TEXT_MAX_LEN):
        if len(messages) >= _LINE_MAX_MESSAGES:
            break
        messages.append({"type": "text", "text": text[i:i + _LINE_TEXT_MAX_LEN]})

    payload = json.dumps({
        "replyToken": reply_token,
        "messages": messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("LINE reply success, status: %d", resp.status)
    except Exception as e:
        logger.error("LINE reply failed: %s", e)
