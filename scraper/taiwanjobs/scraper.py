"""台灣就業通職缺爬蟲

使用 Selenium 處理動態載入的職缺列表，搭配 BeautifulSoup 解析 HTML。
支援關鍵字、地區、產業別篩選，可自動翻頁擷取多頁職缺。

使用方式：
    python -m scraper.taiwanjobs --keyword "餐飲" --pages 3
    python -m scraper.taiwanjobs --keyword "製造" --area "臺北市" --output jobs.json
"""

import argparse
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..models import JobListing
from ..utils import get_logger, save_jobs_to_json, save_jobs_for_career_navigator
from . import config

logger = get_logger(__name__)


class TaiwanJobsScraper(BaseScraper):
    """台灣就業通職缺爬蟲（Selenium 版）"""

    def __init__(self, headless: bool = True, wait_timeout: int = 15):
        """
        Args:
            headless: 是否以無頭模式運行瀏覽器
            wait_timeout: 等待元素載入的最大秒數
        """
        self.wait_timeout = wait_timeout
        self.driver = self._init_driver(headless)
        self.wait = WebDriverWait(self.driver, self.wait_timeout)

    # ------------------------------------------------------------------
    # 公開介面（實作 BaseScraper）
    # ------------------------------------------------------------------

    def search(
        self,
        keyword: str,
        area: str = "",
        max_pages: int = 3,
        *,
        industry: str = "",
        delay: float = 2.0,
        **kwargs,
    ) -> list[JobListing]:
        """搜尋職缺並回傳結果列表

        Args:
            keyword: 搜尋關鍵字（職稱、公司名等）
            area: 地區名稱（如「臺北市」）
            max_pages: 最多爬取幾頁（每頁約 20 筆）
            industry: 產業別
            delay: 每次載入更多後等待的秒數

        Returns:
            職缺列表
        """
        url = self._build_search_url(keyword, area, industry)
        logger.info(f"開始搜尋: {url}")
        self.driver.get(url)
        self._wait_for_jobs_loaded()

        all_jobs: list[JobListing] = []

        for page in range(max_pages):
            logger.info(f"正在擷取第 {page + 1} 頁...")

            page_jobs = self._parse_job_listings()
            new_count = len(page_jobs) - len(all_jobs)
            all_jobs = page_jobs
            logger.info(f"  本頁新增 {new_count} 筆，累計 {len(all_jobs)} 筆")

            if new_count == 0:
                logger.info("沒有更多職缺了，停止載入")
                break

            if page < max_pages - 1:
                if not self._load_more():
                    logger.info("找不到「載入更多」按鈕或已到最後一頁")
                    break
                time.sleep(delay)

        logger.info(f"搜尋完成，共擷取 {len(all_jobs)} 筆職缺")
        return all_jobs

    def get_job_detail(self, detail_url: str) -> dict:
        """取得單筆職缺的詳細資訊"""
        try:
            self.driver.get(detail_url)
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            detail = {}
            content_el = soup.select_one(config.DETAIL_CONTENT_SELECTOR)
            if content_el:
                detail["description"] = content_el.get_text(strip=True)

            condition_el = soup.select_one(config.DETAIL_CONDITION_SELECTOR)
            if condition_el:
                detail["conditions"] = condition_el.get_text(strip=True)

            benefit_el = soup.select_one(config.DETAIL_BENEFIT_SELECTOR)
            if benefit_el:
                detail["benefits"] = benefit_el.get_text(strip=True)

            contact_el = soup.select_one(config.DETAIL_CONTACT_SELECTOR)
            if contact_el:
                detail["contact"] = contact_el.get_text(strip=True)

            return detail
        except Exception as e:
            logger.warning(f"擷取職缺詳情失敗: {e}")
            return {}

    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()
            logger.info("瀏覽器已關閉")

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _init_driver(self, headless: bool) -> webdriver.Chrome:
        """初始化 Chrome WebDriver"""
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=zh-TW")
        options.add_argument(f"--user-agent={config.USER_AGENT}")

        try:
            driver = webdriver.Chrome(options=options)
        except Exception:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        return driver

    def _build_search_url(self, keyword: str, area: str, industry: str) -> str:
        """建構搜尋 URL"""
        params = []
        if keyword:
            params.append(f"keyword={keyword}")
        if area:
            area_code = config.AREA_CODES.get(area, area)
            params.append(f"area={area_code}")
        if industry:
            params.append(f"industry={industry}")

        query = "&".join(params) if params else ""
        return f"{config.BASE_URL}?{query}" if query else config.BASE_URL

    def _wait_for_jobs_loaded(self):
        """等待職缺列表載入完成"""
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, config.WAIT_FOR_SELECTOR)
                )
            )
        except TimeoutException:
            logger.warning("等待職缺載入逾時，嘗試繼續解析...")

    def _parse_job_listings(self) -> list[JobListing]:
        """解析當前頁面上的所有職缺卡片"""
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        jobs = []

        job_elements = []
        for selector in config.JOB_CARD_SELECTORS:
            job_elements = soup.select(selector)
            if job_elements:
                logger.debug(f"使用選擇器 '{selector}' 找到 {len(job_elements)} 筆職缺")
                break

        # 寬鬆搜尋備案
        if not job_elements:
            job_elements = soup.find_all(
                "div",
                class_=lambda c: c and any(
                    kw in (c if isinstance(c, str) else " ".join(c)).lower()
                    for kw in ["job", "card", "item", "vacancy"]
                ),
            )
            if job_elements:
                logger.debug(f"寬鬆搜尋找到 {len(job_elements)} 個可能的職缺區塊")

        for el in job_elements:
            job = self._parse_single_job(el)
            if job and job.title:
                jobs.append(job)

        return jobs

    def _parse_single_job(self, element) -> Optional[JobListing]:
        """解析單一職缺卡片的資訊"""
        try:
            job = JobListing(source=config.SOURCE_NAME)

            # 職稱
            title_el = (
                element.select_one(config.TITLE_SELECTOR)
                or element.select_one(config.TITLE_FALLBACK_SELECTOR)
                or element.find("a")
            )
            if title_el:
                job.title = title_el.get_text(strip=True)
                link = title_el.get("href") or (
                    title_el.find("a") and title_el.find("a").get("href")
                )
                if link:
                    if link.startswith("/"):
                        link = f"https://job.taiwanjobs.gov.tw{link}"
                    job.detail_url = link

            # 公司名稱
            company_el = element.select_one(config.COMPANY_SELECTOR)
            if company_el:
                job.company = company_el.get_text(strip=True)

            # 地點
            location_el = element.select_one(config.LOCATION_SELECTOR)
            if location_el:
                job.location = location_el.get_text(strip=True)

            # 薪資
            salary_el = element.select_one(config.SALARY_SELECTOR)
            if salary_el:
                job.salary = salary_el.get_text(strip=True)

            # 工作型態
            type_el = element.select_one(config.WORK_TYPE_SELECTOR)
            if type_el:
                job.work_type = type_el.get_text(strip=True)

            # 學歷
            edu_el = element.select_one(config.EDUCATION_SELECTOR)
            if edu_el:
                job.education = edu_el.get_text(strip=True)

            # 需求人數
            vacancy_el = element.select_one(config.VACANCY_SELECTOR)
            if vacancy_el:
                job.vacancies = vacancy_el.get_text(strip=True)

            # 日期
            date_el = element.select_one(config.DATE_SELECTOR)
            if date_el:
                job.posted_date = date_el.get_text(strip=True)

            # 備案：從整段文字提取
            if not job.company and not job.salary:
                text = element.get_text(separator="|", strip=True)
                parts = [p.strip() for p in text.split("|") if p.strip()]
                if len(parts) >= 2:
                    if not job.title and parts:
                        job.title = parts[0]
                    if not job.company and len(parts) > 1:
                        job.company = parts[1]

            return job if job.title else None

        except Exception as e:
            logger.debug(f"解析職缺卡片失敗: {e}")
            return None

    def _load_more(self) -> bool:
        """點擊「載入更多職缺」按鈕"""
        try:
            for xpath in config.LOAD_MORE_XPATHS:
                try:
                    btn = self.driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed():
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            btn,
                        )
                        time.sleep(0.5)
                        btn.click()
                        logger.debug(f"已點擊「載入更多」按鈕 (xpath: {xpath})")
                        return True
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            # 備案：滾動到底部觸發無限滾動
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            return True

        except Exception as e:
            logger.debug(f"載入更多失敗: {e}")
            return False


# ----------------------------------------------------------------------
# CLI 進入點
# ----------------------------------------------------------------------

def main():
    """CLI 進入點"""
    parser = argparse.ArgumentParser(
        description="台灣就業通職缺爬蟲 — 擷取 job.taiwanjobs.gov.tw 職缺資料"
    )
    parser.add_argument("--keyword", "-k", default="", help="搜尋關鍵字")
    parser.add_argument("--area", "-a", default="", help="地區（如：臺北市）")
    parser.add_argument("--industry", "-i", default="", help="產業別")
    parser.add_argument("--pages", "-p", type=int, default=3, help="最多擷取幾頁（預設 3）")
    parser.add_argument("--output", "-o", default="", help="輸出 JSON 檔路徑")
    parser.add_argument(
        "--format", "-f", choices=["raw", "career_nav"], default="raw",
        help="輸出格式：raw=原始, career_nav=CareerNav 專案格式",
    )
    parser.add_argument("--no-headless", action="store_true", help="顯示瀏覽器視窗（除錯用）")
    parser.add_argument("--delay", "-d", type=float, default=2.0, help="每頁載入等待秒數")

    args = parser.parse_args()

    if not args.output:
        suffix = f"_{args.keyword}" if args.keyword else ""
        args.output = f"jobs{suffix}.json"

    with TaiwanJobsScraper(headless=not args.no_headless) as scraper:
        jobs = scraper.search(
            keyword=args.keyword,
            area=args.area,
            max_pages=args.pages,
            industry=args.industry,
            delay=args.delay,
        )

    if jobs:
        if args.format == "career_nav":
            save_jobs_for_career_navigator(jobs, args.output)
        else:
            save_jobs_to_json(jobs, args.output)
    else:
        logger.warning("未擷取到任何職缺，請確認搜尋條件或網站是否可正常存取")


if __name__ == "__main__":
    main()
