"""Lambda Chat Proxy — 前端 HTTP → AgentCore 轉接

瀏覽器透過 Function URL 發送 POST 請求，
此 Lambda 轉呼叫 AgentCore invoke_agent API。

環境變數：
    AGENT_ID: AgentCore Agent ID
    AGENT_ALIAS_ID: Agent Alias ID
    AWS_REGION_NAME: AWS Region
"""

import json
import os
import uuid

import boto3


def handler(event: dict, context) -> dict:
    """Lambda handler — 接收前端訊息、轉發給 Agent、回傳結果"""

    # CORS preflight
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": "",
        }

    try:
        body = json.loads(event.get("body", "{}"))
        user_message = body.get("message", "")
        session_id = body.get("session_id", str(uuid.uuid4()))

        if not user_message:
            return _response(400, {"error": "message is required"})

        # 呼叫 AgentCore
        agent_id = os.environ["AGENT_ID"]
        alias_id = os.environ["AGENT_ALIAS_ID"]
        region = os.environ.get("AWS_REGION_NAME", "us-west-2")

        client = boto3.client("bedrock-agent-runtime", region_name=region)

        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=user_message,
        )

        # 收集串流回覆
        completion = ""
        for event_chunk in response.get("completion", []):
            if "chunk" in event_chunk:
                chunk_bytes = event_chunk["chunk"].get("bytes", b"")
                completion += chunk_bytes.decode("utf-8")

        return _response(200, {
            "reply": completion,
            "session_id": session_id,
        })

    except KeyError as e:
        return _response(500, {"error": f"Missing env var: {e}"})
    except Exception as e:
        return _response(500, {"error": str(e)})


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
