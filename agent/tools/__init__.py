"""Career Tools — 六步驟工具模組

匯出所有 tool 函式供 Agent 使用。
後續 Task 3 會實作完整邏輯。
"""

from .career_tools import (
    analyze_profile,
    match_resources,
    calculate_benefit,
    generate_roadmap,
    get_checklist,
    send_notification,
)

# Agent 載入用的工具清單
TOOL_REGISTRY = [
    analyze_profile,
    match_resources,
    calculate_benefit,
    generate_roadmap,
    get_checklist,
    send_notification,
]

__all__ = [
    "TOOL_REGISTRY",
    "analyze_profile",
    "match_resources",
    "calculate_benefit",
    "generate_roadmap",
    "get_checklist",
    "send_notification",
]
