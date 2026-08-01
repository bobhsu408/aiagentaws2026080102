"""六步驟 Career Tools — 骨架實作

每個 tool 使用 @tool 裝飾器，提供給 Strands Agent 呼叫。
Task 3 會填入完整業務邏輯，這裡先確保介面正確。
"""

import json
from pathlib import Path
from typing import Any

from strands import tool

# 資料路徑（相對於此檔案）
DATA_DIR = Path(__file__).parent.parent / "data"


def _load_resources() -> list[dict]:
    """載入補助資料"""
    resources_path = DATA_DIR / "resources.json"
    if not resources_path.exists():
        return []
    with open(resources_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_constants() -> dict:
    """載入全局常數"""
    constants_path = DATA_DIR / "constants.json"
    if not constants_path.exists():
        return {"monthly_min_wage": 28590, "hourly_min_wage": 190}
    with open(constants_path, "r", encoding="utf-8") as f:
        return json.load(f)


@tool
def analyze_profile(user_description: str) -> dict:
    """解析使用者自然語言描述，萃取結構化背景資料。

    Args:
        user_description: 使用者用自然語言描述的個人狀況

    Returns:
        結構化的使用者背景 profile（年齡、產業、年資、離職原因等）
    """
    # TODO: Task 3 實作完整解析邏輯
    return {
        "status": "skeleton",
        "message": "analyze_profile 骨架 — 待 Task 3 實作",
        "input_received": user_description[:100],
    }


@tool
def match_resources(profile: dict) -> dict:
    """根據使用者 profile 匹配符合資格的補助方案。

    Args:
        profile: 由 analyze_profile 產出的結構化背景

    Returns:
        符合資格的補助方案清單
    """
    resources = _load_resources()
    # TODO: Task 3 實作完整匹配邏輯
    return {
        "status": "skeleton",
        "message": "match_resources 骨架 — 待 Task 3 實作",
        "total_resources_loaded": len(resources),
    }


@tool
def calculate_benefit(matched_ids: list[str], profile: dict) -> dict:
    """試算使用者可領取的金額。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        各方案的金額試算結果
    """
    constants = _load_constants()
    # TODO: Task 3 實作完整計算邏輯
    return {
        "status": "skeleton",
        "message": "calculate_benefit 骨架 — 待 Task 3 實作",
        "min_wage_used": constants["monthly_min_wage"],
    }


@tool
def generate_roadmap(matched_ids: list[str], profile: dict) -> dict:
    """產出 1~6 個月的時間軸行動計畫。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        分月份的行動計畫
    """
    # TODO: Task 3 實作完整 roadmap 邏輯
    return {
        "status": "skeleton",
        "message": "generate_roadmap 骨架 — 待 Task 3 實作",
    }


@tool
def get_checklist(matched_ids: list[str]) -> dict:
    """回傳申請各補助方案所需的文件清單。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表

    Returns:
        各方案的應備文件清單
    """
    resources = _load_resources()
    # TODO: Task 3 實作完整 checklist 邏輯
    return {
        "status": "skeleton",
        "message": "get_checklist 骨架 — 待 Task 3 實作",
    }


@tool
def send_notification(email: str, summary: str) -> dict:
    """傳送行動計畫摘要通知（demo 模擬）。

    Args:
        email: 使用者 email
        summary: 行動計畫摘要文字

    Returns:
        通知發送狀態
    """
    # Demo 模式：不實際發送，僅模擬成功
    return {
        "status": "success",
        "message": f"（模擬）已將行動計畫摘要寄送至 {email}",
        "demo_mode": True,
    }
