"""共用工具函式

提供存檔、logging 設定等各爬蟲共用的功能。
"""

import json
import logging
from pathlib import Path

from .models import JobListing


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """取得已設定格式的 logger"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return logging.getLogger(name)


def save_jobs_to_json(jobs: list[JobListing], output_path: str) -> None:
    """將職缺列表存為 JSON 檔案（原始格式）

    Args:
        jobs: 職缺列表
        output_path: 輸出路徑
    """
    data = [job.to_dict() for job in jobs]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger = get_logger(__name__)
    logger.info(f"已儲存 {len(data)} 筆職缺到 {path}")


def save_jobs_for_career_navigator(jobs: list[JobListing], output_path: str) -> None:
    """將職缺轉換為 career_navigator 專案格式並儲存

    輸出格式與 data/resources.json 相容，方便 Agent 使用。

    Args:
        jobs: 職缺列表
        output_path: 輸出路徑
    """
    resources = []
    for i, job in enumerate(jobs):
        job_id = f"job_{i + 1:04d}"
        resources.append(job.to_career_nav_format(job_id))

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resources, f, ensure_ascii=False, indent=2)
    logger = get_logger(__name__)
    logger.info(f"已儲存 {len(resources)} 筆職缺資源到 {path}")
