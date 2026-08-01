# 資料擷取模組

多來源資料擷取，採統一介面設計，方便擴充新來源。

**這些腳本在本機離線執行，產出結構化 JSON 供 Agent Runtime 使用。**

---

## 目錄結構

```
scraper/
├── __init__.py          # 統一進入點 & SCRAPERS 註冊表
├── base.py              # BaseScraper 抽象介面
├── models.py            # 共用資料結構（JobListing）
├── utils.py             # 共用工具（存檔、logging）
├── requirements.txt
├── README.md
│
├── taiwanjobs/           # 台灣就業通（職缺）
│   ├── __init__.py
│   ├── config.py         # URL、選擇器、地區代碼等常數
│   └── scraper.py        # TaiwanJobsScraper 主邏輯
│
└── laws/                 # 全國法規資料庫（就業相關法規）
    ├── __init__.py
    ├── config.py         # API 端點、目標法規清單、正則
    └── scraper.py        # LawsScraper 主邏輯
```

## 安裝

```bash
pip install -r scraper/requirements.txt
```

台灣就業通爬蟲需要系統已安裝 Chrome 瀏覽器。法規擷取只用 Python 標準庫，無額外依賴。

---

## 快速使用

### Python API

```python
from scraper import TaiwanJobsScraper, LawsScraper, SCRAPERS

# 職缺搜尋
with TaiwanJobsScraper() as s:
    jobs = s.search("餐飲", area="臺北市", max_pages=3)

for job in jobs:
    print(f"{job.title} @ {job.company} — {job.salary}")

# 法規擷取
with LawsScraper() as s:
    result = s.extract()
    print(f"共 {result['metadata']['extracted_laws_count']} 部法規")
    print(f"含金額條文 {result['metadata']['money_articles_count']} 條")

# 動態選擇來源
ScraperClass = SCRAPERS["taiwanjobs"]
with ScraperClass() as s:
    jobs = s.search("製造")
```

### CLI — 台灣就業通

```bash
# 基本搜尋
python -m scraper.taiwanjobs.scraper --keyword "餐飲"

# 指定地區 + 多頁
python -m scraper.taiwanjobs.scraper --keyword "製造" --area "臺中市" --pages 5

# 輸出為 CareerNav 專案格式
python -m scraper.taiwanjobs.scraper --keyword "資訊" --format career_nav --output data/jobs.json

# 顯示瀏覽器視窗（除錯用）
python -m scraper.taiwanjobs.scraper --keyword "服務" --no-headless
```

### CLI — 法規擷取

```bash
# 預設輸出到 output/laws_extracted.json
python -m scraper.laws.scraper

# 指定輸出路徑
python -m scraper.laws.scraper --output data/laws.json
```

---

## CLI 參數

### 台灣就業通

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--keyword`, `-k` | 搜尋關鍵字 | 空（全部） |
| `--area`, `-a` | 地區名稱（臺北市、新北市等） | 空（全部） |
| `--industry`, `-i` | 產業別 | 空（全部） |
| `--pages`, `-p` | 最多擷取頁數 | 3 |
| `--output`, `-o` | 輸出 JSON 檔路徑 | 自動命名 |
| `--format`, `-f` | 輸出格式（raw / career_nav） | raw |
| `--delay`, `-d` | 每頁載入間隔秒數 | 2.0 |
| `--no-headless` | 顯示瀏覽器視窗 | 否 |

### 法規擷取

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--output`, `-o` | 輸出 JSON 路徑 | `output/laws_extracted.json` |

---

## 新增網站

三步完成：

1. **建立子資料夾**（如 `scraper/_104/`），包含 `__init__.py`、`config.py`、`scraper.py`
2. **實作 `BaseScraper` 介面** — 必須實作 `search()` 和 `close()`
3. **註冊到 `scraper/__init__.py`** 的 `SCRAPERS` 字典

```python
# scraper/_104/scraper.py
from ..base import BaseScraper
from ..models import JobListing

class Job104Scraper(BaseScraper):
    def search(self, keyword, area="", max_pages=3, **kwargs) -> list[JobListing]:
        ...

    def close(self):
        ...
```

```python
# scraper/__init__.py — 加入
from ._104 import Job104Scraper

SCRAPERS["104"] = Job104Scraper
```

---

## 設計原則

- **統一資料結構**：職缺來源回傳 `JobListing`，下游不需關心差異
- **選擇器獨立**：容易變動的 CSS/XPath 放在各網站的 `config.py`，改版時只改 config
- **共用工具**：存檔、logging 等通用邏輯集中在 `utils.py`
- **爬蟲禮儀**：職缺爬蟲預設每頁間隔 2 秒，不過度頻繁請求
- **法規 API 免認證**：可在任何環境執行，不需瀏覽器

## 注意事項

1. 台灣就業通的職缺列表主要透過 JavaScript 動態載入，需要 Selenium + Chrome
2. 網站可能更新 HTML 結構，屆時調整對應的 `config.py` 選擇器即可
3. 子資料夾名稱避免用純數字開頭（如用 `_104/` 而非 `104/`）
4. `output/` 建議加入 `.gitignore`，擷取結果不需提交到 repo
