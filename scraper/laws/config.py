"""法規擷取 — 常數與設定

API 端點（免認證）：
    - 法律: https://law.moj.gov.tw/api/Ch/Law/JSON   (~6MB ZIP)
    - 命令: https://law.moj.gov.tw/api/Ch/Order/JSON  (~25MB ZIP)
"""

# API 端點
LAW_API = "https://law.moj.gov.tw/api/Ch/Law/JSON"
ORDER_API = "https://law.moj.gov.tw/api/Ch/Order/JSON"

# 來源名稱
SOURCE_NAME = "全國法規資料庫"

# 目標法規名稱（精確匹配）
TARGET_LAWS: list[str] = [
    "就業保險法",
    "就業服務法",
    "職業訓練法",
    "中高齡者及高齡者就業促進法",
    "身心障礙者權益保障法",
]

TARGET_ORDERS: list[str] = [
    "就業促進津貼實施辦法",
    "就業保險促進就業實施辦法",
    "失業中高齡者及高齡者就業促進辦法",
    "就業保險失業者創業協助辦法",
    "身心障礙者職務再設計實施方式及補助準則",
    "育嬰留職停薪實施辦法",
    "失業被保險人及其眷屬全民健康保險保險費補助辦法",
    "就業保險延長失業給付實施辦法",
    "促進中高齡者及高齡者就業獎勵辦法",
]

# 金額 / 比例相關的正則（用於篩選含補助資訊的條文）
MONEY_PATTERN = r"新臺幣|百分之|萬元|月薪|元[。，]|最低工資|投保薪資"
