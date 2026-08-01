"""六步驟 Career Tools — Strands @tool 封裝

本檔僅做薄封裝：以 @tool 裝飾器暴露給 Strands Agent，
實際業務邏輯位於 logic.py（不依賴 strands，方便獨立測試）。
"""

from strands import tool

from . import logic


@tool
def analyze_profile(user_description: str) -> dict:
    """解析使用者自然語言描述，萃取結構化背景資料。

    此工具做盡力而為的關鍵字萃取，並回報還缺哪些判斷資格的關鍵欄位；
    Agent 應根據 missing_fields 主動追問使用者。

    Args:
        user_description: 使用者用自然語言描述的個人狀況

    Returns:
        含 profile、missing_fields、target_groups、guidance 的 dict。
    """
    return logic.analyze_profile(user_description)


@tool
def match_resources(profile: dict, include_employer: bool = False) -> dict:
    """根據使用者 profile 匹配符合資格的補助方案。

    預設只回傳發給勞工（recipient == "勞工"）的方案；若使用者明確詢問
    雇主可申請的獎助，可將 include_employer 設為 True。

    Args:
        profile: 由 analyze_profile 產出的結構化背景
        include_employer: 是否納入發給雇主的方案（預設 False）

    Returns:
        含 matched、excluded、concurrency_warnings、total_matched 的 dict。
    """
    return logic.match_resources(profile, include_employer)


@tool
def calculate_benefit(matched_ids: list[str], profile: dict) -> dict:
    """試算使用者可領取的金額。

    讀 benefit.base，依 profile 套用 conditional_tiers，再加算 surcharges。
    缺少計算所需數值時，回傳公式並標記 needs_input，同時以基本工資作
    保守下限估算（標記 assumption），供 Agent 說明。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        含 calculations、concurrency_notes、disclaimer 的 dict。
    """
    return logic.calculate_benefit(matched_ids, profile)


@tool
def generate_roadmap(matched_ids: list[str], profile: dict) -> dict:
    """產出 1~6 個月的時間軸行動計畫。

    採兩段式課程呈現：curated（courses.json 篩出的計畫層級課程）與
    hint（即時搜尋關鍵字，實際開課梯次由 Agent 即時搜尋補充）。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        含 timeline、decision_points、courses、total_months 的 dict。
    """
    return logic.generate_roadmap(matched_ids, profile)


@tool
def get_checklist(matched_ids: list[str]) -> dict:
    """回傳申請各補助方案所需的文件清單（去重、分類）。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表

    Returns:
        含 common_documents、per_resource、tips 的 dict。
    """
    return logic.get_checklist(matched_ids)


@tool
def send_notification(summary: str, email: str = "", line_user_id: str = "") -> dict:
    """傳送行動計畫摘要通知（展示模式）。

    目前為 demo 模擬：不實際寄信或推播，僅回傳成功狀態。介面預留
    line_user_id 參數，未來可接入 LINE Messaging API 真正推播。

    Args:
        summary: 行動計畫摘要文字
        email: 收件 email（展示用）
        line_user_id: LINE 使用者 ID（保留擴充，目前未啟用）

    Returns:
        含 status、channel、demo_mode、sent_at 的 dict。
    """
    return logic.send_notification(summary, email, line_user_id)


# 工具註冊表（供 main.py 載入）
TOOL_REGISTRY = [
    analyze_profile,
    match_resources,
    calculate_benefit,
    generate_roadmap,
    get_checklist,
    send_notification,
]
