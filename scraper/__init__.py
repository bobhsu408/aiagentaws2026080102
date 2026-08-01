"""職缺爬蟲模組 — 多網站統一介面

新增網站只需三步：
1. 建立子資料夾（如 scraper/yourator/）
2. 實作 BaseScraper 介面
3. 在此處註冊到 SCRAPERS 字典

使用範例：
    from scraper import SCRAPERS, TaiwanJobsScraper, LawsScraper

    # 職缺搜尋
    with TaiwanJobsScraper() as s:
        jobs = s.search("餐飲", area="臺北市")

    # 法規擷取
    with LawsScraper() as s:
        result = s.extract()

    # 動態選擇來源
    ScraperClass = SCRAPERS["taiwanjobs"]
    with ScraperClass() as s:
        jobs = s.search("製造")
"""

from .base import BaseScraper
from .models import JobListing
from .taiwanjobs import TaiwanJobsScraper
from .laws import LawsScraper

# 已註冊的爬蟲 — key 為來源識別碼
SCRAPERS: dict[str, type[BaseScraper]] = {
    "taiwanjobs": TaiwanJobsScraper,
    "laws": LawsScraper,
}

__all__ = [
    "BaseScraper",
    "JobListing",
    "TaiwanJobsScraper",
    "LawsScraper",
    "SCRAPERS",
]
