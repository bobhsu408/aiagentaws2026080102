"""爬蟲基底類別

所有網站爬蟲都應繼承 BaseScraper 並實作其抽象方法，
確保呼叫端可以用統一的介面操作任何來源。
"""

from abc import ABC, abstractmethod

from .models import JobListing


class BaseScraper(ABC):
    """爬蟲抽象介面

    使用方式：
        with SomeSiteScraper() as scraper:
            jobs = scraper.search("關鍵字", area="臺北市", max_pages=3)
    """

    @abstractmethod
    def search(
        self,
        keyword: str,
        area: str = "",
        max_pages: int = 3,
        **kwargs,
    ) -> list[JobListing]:
        """搜尋職缺

        Args:
            keyword: 搜尋關鍵字（職稱、技能、公司名等）
            area: 地區篩選
            max_pages: 最多擷取頁數

        Returns:
            統一格式的職缺列表
        """
        ...

    @abstractmethod
    def close(self):
        """釋放資源（關閉瀏覽器、session 等）"""
        ...

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
