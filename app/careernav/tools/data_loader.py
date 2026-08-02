"""資料載入模組

負責讀取 data/ 目錄下的 resources.json、constants.json、courses.json，
提供給六步驟 Career Tools 使用。採用模組層級快取，避免重複讀檔。
"""

import json
from pathlib import Path
from typing import Any

# data/ 目錄位於本套件的上一層（app/careernav/data）
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 模組層級快取
_CACHE: dict[str, Any] = {}

# 最低工資的保底預設值（讀檔失敗時使用，2026 年公告值）
_FALLBACK_CONSTANTS: dict[str, Any] = {
    "year": 2026,
    "monthly_min_wage": 29500,
    "hourly_min_wage": 196,
}


def _read_json(filename: str, default: Any) -> Any:
    """讀取 data/ 下的 JSON 檔，失敗時回傳 default。

    Args:
        filename: 檔名（例：resources.json）
        default: 讀檔失敗時的預設值

    Returns:
        解析後的 JSON 物件，或 default
    """
    path = _DATA_DIR / filename
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def load_resources() -> list[dict]:
    """載入補助方案清單（resources.json）。

    Returns:
        補助方案 dict 的清單；讀檔失敗時回傳空清單。
    """
    if "resources" not in _CACHE:
        _CACHE["resources"] = _read_json("resources.json", [])
    return _CACHE["resources"]


def load_constants() -> dict:
    """載入全局常數（constants.json）。

    Returns:
        常數 dict；讀檔失敗時回傳 2026 年保底值。
    """
    if "constants" not in _CACHE:
        _CACHE["constants"] = _read_json("constants.json", dict(_FALLBACK_CONSTANTS))
    return _CACHE["constants"]


def load_courses() -> list[dict]:
    """載入課程樣本資料（courses.json）。

    Returns:
        課程 dict 的清單（取 courses 欄位）；讀檔失敗時回傳空清單。
    """
    if "courses" not in _CACHE:
        raw = _read_json("courses.json", {})
        _CACHE["courses"] = raw.get("courses", []) if isinstance(raw, dict) else []
    return _CACHE["courses"]


def get_resource_by_id(resource_id: str) -> dict | None:
    """依 id 取得單一補助方案。

    Args:
        resource_id: 補助方案的唯一識別碼

    Returns:
        對應的方案 dict，找不到時回傳 None。
    """
    for res in load_resources():
        if res.get("id") == resource_id:
            return res
    return None


def clear_cache() -> None:
    """清除模組快取（測試用）。"""
    _CACHE.clear()
