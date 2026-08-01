"""共用資料結構

所有網站爬蟲回傳的職缺資料都應轉換為此處定義的統一格式，
確保下游（Agent、API、前端）不需要關心資料來源差異。
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class JobListing:
    """單筆職缺資料的統一格式"""

    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    work_type: str = ""          # 全職 / 兼職 / 部份工時
    education: str = ""          # 學歷要求
    experience: str = ""         # 經驗要求
    description: str = ""        # 工作內容摘要
    benefits: str = ""           # 福利
    contact: str = ""            # 聯絡方式
    detail_url: str = ""         # 職缺詳情連結
    source: str = ""             # 來源網站名稱
    industry: str = ""           # 產業別
    vacancies: str = ""          # 需求人數
    posted_date: str = ""        # 刊登日期
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """轉為 dict（方便 JSON 序列化）"""
        return asdict(self)

    def to_career_nav_format(self, job_id: str = "") -> dict:
        """轉為 career_navigator 專案使用的格式

        與 data/resources.json 結構相容。
        """
        return {
            "id": job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "work_type": self.work_type,
            "education": self.education,
            "industry": self.industry,
            "vacancies": self.vacancies,
            "posted_date": self.posted_date,
            "detail_url": self.detail_url,
            "source": self.source,
            "description": self.description,
        }
