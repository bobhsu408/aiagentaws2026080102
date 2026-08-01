"""法規資料擷取器

從全國法規資料庫 API 下載法律與命令，篩選就業/職訓相關法規，
萃取資格條件與金額公式，輸出結構化 JSON。

使用方式：
    python -m scraper.laws.scraper
    python -m scraper.laws.scraper --output output/laws_extracted.json
"""

import argparse
import io
import json
import re
import urllib.request
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from ..base import BaseScraper
from ..models import JobListing
from ..utils import get_logger
from . import config

logger = get_logger(__name__)


# --- 法規專用資料結構 ---


@dataclass
class LawArticle:
    """單一條文"""
    law_name: str = ""
    article_no: str = ""
    content: str = ""
    url: str = ""


@dataclass
class LawDocument:
    """單部法規"""
    name: str = ""
    level: str = ""
    category: str = ""
    modified_date: str = ""
    url: str = ""
    article_count: int = 0
    articles: list[dict] = field(default_factory=list)


# --- 主類別 ---


class LawsScraper(BaseScraper):
    """法規資料擷取器

    與其他爬蟲不同，這個類別不搜尋職缺，而是擷取法規條文。
    實作 BaseScraper 是為了統一管理介面（生命週期、進入點）。

    使用方式：
        with LawsScraper() as scraper:
            result = scraper.extract()
    """

    def __init__(self):
        self._session_open = True

    # ------------------------------------------------------------------
    # BaseScraper 介面實作
    # ------------------------------------------------------------------

    def search(
        self,
        keyword: str = "",
        area: str = "",
        max_pages: int = 1,
        **kwargs,
    ) -> list[JobListing]:
        """BaseScraper 介面 — 法規擷取不使用此方法，請用 extract()。

        為了相容性，回傳空列表。
        """
        logger.info("LawsScraper.search() 被呼叫 — 法規模組請改用 extract() 方法")
        return []

    def close(self):
        """釋放資源"""
        self._session_open = False
        logger.info("LawsScraper 已關閉")

    # ------------------------------------------------------------------
    # 法規專用方法
    # ------------------------------------------------------------------

    def extract(
        self,
        target_laws: Optional[list[str]] = None,
        target_orders: Optional[list[str]] = None,
    ) -> dict:
        """擷取法規資料

        Args:
            target_laws: 要篩選的法律名稱（預設使用 config 內建清單）
            target_orders: 要篩選的命令名稱（預設使用 config 內建清單）

        Returns:
            包含 metadata、laws、money_articles 的字典
        """
        if target_laws is None:
            target_laws = config.TARGET_LAWS
        if target_orders is None:
            target_orders = config.TARGET_ORDERS

        # 下載法律
        logger.info("=== 下載法律 ===")
        law_data = self._download_and_parse(config.LAW_API)
        target_law_docs = self._filter_laws(law_data["Laws"], target_laws)

        # 下載命令
        logger.info("=== 下載命令 ===")
        order_data = self._download_and_parse(config.ORDER_API)
        target_order_docs = self._filter_laws(order_data["Laws"], target_orders)

        # 合併
        all_target = target_law_docs + target_order_docs
        logger.info(f"共篩選到 {len(all_target)} 部法規")

        # 萃取金額相關條文
        all_money_articles = []
        for law in all_target:
            articles = self._extract_money_articles(law)
            all_money_articles.extend(articles)
        logger.info(f"含金額/比例的條文共 {len(all_money_articles)} 條")

        # 組裝結果
        result = {
            "metadata": {
                "source": config.SOURCE_NAME,
                "law_update_date": law_data["UpdateDate"],
                "order_update_date": order_data["UpdateDate"],
                "extracted_laws_count": len(all_target),
                "money_articles_count": len(all_money_articles),
            },
            "laws": [
                {
                    "name": l["LawName"],
                    "level": l["LawLevel"],
                    "category": l["LawCategory"],
                    "modified_date": l["LawModifiedDate"],
                    "url": l["LawURL"],
                    "article_count": len(l["LawArticles"]),
                    "articles": [
                        {
                            "no": a["ArticleNo"].strip(),
                            "content": a["ArticleContent"],
                        }
                        for a in l["LawArticles"]
                        if a["ArticleType"] == "A"
                    ],
                }
                for l in all_target
            ],
            "money_articles": [asdict(a) for a in all_money_articles],
        }

        return result

    def extract_and_save(self, output_path: str = "output/laws_extracted.json") -> dict:
        """擷取並儲存到 JSON 檔案

        Args:
            output_path: 輸出路徑

        Returns:
            擷取結果字典
        """
        result = self.extract()

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"輸出完成: {path} ({path.stat().st_size / 1024:.0f} KB)")
        return result

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _download_and_parse(self, url: str) -> dict:
        """下載 ZIP 並解析 JSON"""
        logger.info(f"下載中: {url}")
        data = urllib.request.urlopen(url, timeout=120).read()
        z = zipfile.ZipFile(io.BytesIO(data))
        json_file = [n for n in z.namelist() if n.endswith(".json")][0]
        content = json.loads(z.read(json_file).decode("utf-8-sig"))
        logger.info(f"  完成，共 {len(content['Laws'])} 筆，更新日 {content['UpdateDate']}")
        return content

    def _filter_laws(self, all_laws: list[dict], target_names: list[str]) -> list[dict]:
        """依名稱篩選目標法規"""
        result = []
        for name in target_names:
            matches = [l for l in all_laws if l["LawName"] == name]
            if matches:
                result.append(matches[0])
                logger.info(f"  ✓ {name} ({len(matches[0]['LawArticles'])} 條)")
            else:
                logger.warning(f"  ✗ {name} — 未找到")
        return result

    def _extract_money_articles(self, law: dict) -> list[LawArticle]:
        """從法規中萃取含金額/比例的條文"""
        results = []
        for art in law["LawArticles"]:
            if art["ArticleType"] != "A":
                continue
            content = art["ArticleContent"]
            if re.search(config.MONEY_PATTERN, content):
                results.append(LawArticle(
                    law_name=law["LawName"],
                    article_no=art["ArticleNo"].strip(),
                    content=content,
                    url=law["LawURL"],
                ))
        return results


# ----------------------------------------------------------------------
# CLI 進入點
# ----------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="從全國法規資料庫擷取就業相關法規"
    )
    parser.add_argument(
        "--output", "-o",
        default="output/laws_extracted.json",
        help="輸出 JSON 路徑（預設 output/laws_extracted.json）",
    )
    args = parser.parse_args()

    with LawsScraper() as scraper:
        scraper.extract_and_save(args.output)


if __name__ == "__main__":
    main()
