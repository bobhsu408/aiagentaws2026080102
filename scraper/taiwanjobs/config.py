"""台灣就業通 — 網站常數與設定

把容易因網站改版而變動的東西集中在這裡，
修改時只動 config 不動爬蟲邏輯。
"""

# 搜尋頁面 base URL
BASE_URL = "https://job.taiwanjobs.gov.tw/Internet/Index/job_search_list.aspx"

# 地區代碼對照表（常用縣市）
AREA_CODES: dict[str, str] = {
    "臺北市": "01",
    "新北市": "02",
    "桃園市": "03",
    "臺中市": "04",
    "臺南市": "05",
    "高雄市": "06",
    "基隆市": "07",
    "新竹市": "08",
    "新竹縣": "09",
    "苗栗縣": "10",
    "彰化縣": "11",
    "南投縣": "12",
    "雲林縣": "13",
    "嘉義市": "14",
    "嘉義縣": "15",
    "屏東縣": "16",
    "宜蘭縣": "17",
    "花蓮縣": "18",
    "臺東縣": "19",
    "澎湖縣": "20",
    "金門縣": "21",
    "連江縣": "22",
}

# 來源名稱（寫入 JobListing.source）
SOURCE_NAME = "台灣就業通"

# --- CSS 選擇器 ---
# 職缺卡片（依優先順序嘗試）
JOB_CARD_SELECTORS: list[str] = [
    ".job-card",
    ".job-item",
    ".job-list-item",
    "[class*='jobCard']",
    "[class*='job-card']",
    ".card[data-jobno]",
    "div[class*='Job']",
    ".list-group-item",
    "article",
]

# 單一卡片內的欄位選擇器
TITLE_SELECTOR = "h2 a, h3 a, h4 a, .job-title, [class*='title'] a, a[title]"
TITLE_FALLBACK_SELECTOR = "h2, h3, h4, .job-title, [class*='title']"
COMPANY_SELECTOR = ".company-name, [class*='company'], [class*='corp'], .employer"
LOCATION_SELECTOR = ".job-location, [class*='location'], [class*='area'], [class*='addr']"
SALARY_SELECTOR = ".salary, [class*='salary'], [class*='pay'], [class*='wage']"
WORK_TYPE_SELECTOR = "[class*='type'], [class*='worktime'], .badge"
EDUCATION_SELECTOR = "[class*='edu'], [class*='degree']"
VACANCY_SELECTOR = "[class*='vacanc'], [class*='people'], [class*='num']"
DATE_SELECTOR = "[class*='date'], [class*='time'], time"

# 詳情頁面選擇器
DETAIL_CONTENT_SELECTOR = ".job-content, .work-content, [class*='content']"
DETAIL_CONDITION_SELECTOR = ".job-condition, [class*='condition']"
DETAIL_BENEFIT_SELECTOR = ".job-benefit, [class*='benefit'], [class*='welfare']"
DETAIL_CONTACT_SELECTOR = ".contact-info, [class*='contact']"

# 載入更多按鈕（XPath）
LOAD_MORE_XPATHS: list[str] = [
    "//button[contains(text(), '載入更多')]",
    "//a[contains(text(), '載入更多')]",
    "//div[contains(text(), '載入更多')]",
    "//button[contains(@class, 'more')]",
    "//a[contains(@class, 'more')]",
    "//button[contains(@class, 'load')]",
]

# 等待頁面載入的選擇器
WAIT_FOR_SELECTOR = ".job-card, .job-item, .job-list-item, [class*='job'], .card"

# --- 瀏覽器設定 ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# requests 版的 headers
REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}
