"""使用者 profile 模組

定義 analyze_profile 的輸出 schema、profile 與 resources.json eligibility
欄位之間的對應關係，以及自然語言的啟發式萃取邏輯。

設計說明：
    真正的語言理解由 Agent（Claude）完成——它會在對話中主動追問並整理資訊。
    本模組提供「規範化的 profile 結構」與「盡力而為的關鍵字萃取」，
    確保下游工具（match_resources / calculate_benefit）有明確的 input schema，
    並透過 missing_fields 告訴 Agent 還缺哪些判斷資格的關鍵資訊。
"""

import re

# ----------------------------------------------------------------------------
# Profile 預設 schema
# ----------------------------------------------------------------------------
# 值為 None 代表尚未取得；布林 / 數值型有明確預設。
PROFILE_SCHEMA: dict = {
    "age": None,                    # int，年齡
    "gender": None,                 # "男" / "女"
    "industry": None,               # 離職前產業
    "job_title": None,              # 離職前職稱
    "years_of_experience": None,    # float，年資
    "leave_reason": None,           # "非自願" / "自願" / "育嬰" / "退休"
    "insurance_months": None,       # int，就業保險年資（月）
    "has_disability_cert": False,   # 是否持身心障礙證明
    "has_young_children": False,    # 是否育有幼兒
    "dependents_count": 0,          # 受扶養眷屬人數
    "avg_insured_salary": None,     # int，離職前平均月投保薪資
    "target_industry": None,        # 想轉入的產業
    "location": None,               # 居住地
    "is_indigenous": False,         # 是否原住民
    "education_level": None,        # 學歷
    # 由對話推導、供計算用的輔助欄位
    "insurance_status": None,       # "ei"（就業保險身分）/ "non_ei"
    "monthly_rent": None,           # int，就業地租金（租屋補助試算用）
}

# ----------------------------------------------------------------------------
# profile 欄位 → eligibility 欄位 對應表
# ----------------------------------------------------------------------------
# match_resources 依此表把 profile 對映到 resources.json 的 eligibility 條件。
# 格式：eligibility 欄位名 -> 說明如何從 profile 判斷。
FIELD_MAPPING: dict[str, str] = {
    "min_age": "profile['age'] >= eligibility['min_age']",
    "max_age": "profile['age'] <= eligibility['max_age']",
    "min_insurance_months": "profile['insurance_months'] >= eligibility['min_insurance_months']",
    "requires_involuntary_leave": "profile['leave_reason'] == '非自願'",
    "requires_disability_cert": "profile['has_disability_cert'] is True",
    "requires_young_children": "profile['has_young_children'] is True",
    "requires_business_plan": "由對話確認是否有創業計畫（profile 無對應布林，預設待確認）",
    "requires_fulltime_training": "由對話確認是否已安排全日制職訓（預設待確認）",
    "requires_parental_leave": "profile['leave_reason'] == '育嬰'",
    "requires_active_job_search": "預設使用者願意配合就服站求職登記（申辦動作，非資格門檻）",
    "target_groups": "由 age / gender / has_disability_cert / is_indigenous 推導所屬群體",
}

# 年齡 → target_group 推導門檻
_MID_AGE_MIN = 45   # 中高齡下限
_SENIOR_MIN = 65    # 高齡下限
_YOUTH_MAX = 29     # 青年上限


def derive_target_groups(profile: dict) -> list[str]:
    """由 profile 推導使用者所屬的 target_group 標籤。

    Args:
        profile: 使用者 profile

    Returns:
        target_group 標籤清單（可能多個），永遠包含 "一般"。
    """
    groups: list[str] = ["一般"]
    age = profile.get("age")
    if isinstance(age, (int, float)):
        if age >= _SENIOR_MIN:
            groups.append("高齡")
        elif age >= _MID_AGE_MIN:
            groups.append("中高齡")
        elif age <= _YOUTH_MAX:
            groups.append("青年")
    if profile.get("gender") == "女":
        groups.append("婦女")
    if profile.get("has_disability_cert"):
        groups.append("身心障礙")
    if profile.get("is_indigenous"):
        groups.append("原住民")
    return groups


# 判斷資格時最關鍵、缺了就難以判斷的欄位
_KEY_FIELDS_FOR_ELIGIBILITY = [
    "age",
    "leave_reason",
    "insurance_months",
]


def compute_missing_fields(profile: dict) -> list[str]:
    """找出判斷資格所需但 profile 尚缺的關鍵欄位。

    Args:
        profile: 使用者 profile

    Returns:
        缺少的關鍵欄位名清單。
    """
    missing = []
    for field in _KEY_FIELDS_FOR_ELIGIBILITY:
        if profile.get(field) in (None, ""):
            missing.append(field)
    return missing


# ----------------------------------------------------------------------------
# 啟發式萃取（盡力而為，Agent 會補足）
# ----------------------------------------------------------------------------
_CHINESE_NUM = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _to_int(text: str) -> int | None:
    """將阿拉伯數字或簡單中文數字字串轉為 int。"""
    text = text.strip()
    if text.isdigit():
        return int(text)
    if text in _CHINESE_NUM:
        return _CHINESE_NUM[text]
    return None


def extract_profile(text: str) -> dict:
    """從自然語言描述啟發式萃取 profile 欄位。

    此為盡力而為的規則式萃取，無法涵蓋所有語句；Agent 會在對話中
    主動追問補足 missing_fields。

    Args:
        text: 使用者的自然語言描述

    Returns:
        填入可萃取欄位的 profile dict（含 missing_fields）。
    """
    profile = dict(PROFILE_SCHEMA)

    # 年齡：「58歲」「58 歲」「年齡58」
    age_match = re.search(r"(\d{1,2})\s*歲", text)
    if age_match:
        profile["age"] = int(age_match.group(1))

    # 性別
    if re.search(r"女性|女生|婦女|太太|媽媽|阿姨", text):
        profile["gender"] = "女"
    elif re.search(r"男性|男生|先生|爸爸|大哥", text):
        profile["gender"] = "男"

    # 離職原因
    if re.search(r"資遣|裁員|解僱|解雇|關廠|歇業|非自願|被迫離職|公司倒", text):
        profile["leave_reason"] = "非自願"
        profile["insurance_status"] = "ei"
    elif re.search(r"育嬰|留職停薪|生小孩|坐月子", text):
        profile["leave_reason"] = "育嬰"
    elif re.search(r"退休", text):
        profile["leave_reason"] = "退休"
    elif re.search(r"自願離職|自己辭|想離職|主動離職", text):
        profile["leave_reason"] = "自願"

    # 保險年資：「保了20年」「投保 20 年」「年資15年」→ 換算月數
    ins_year = re.search(r"(?:保|投保|就保|年資).{0,4}?(\d{1,2})\s*年", text)
    if ins_year:
        profile["insurance_months"] = int(ins_year.group(1)) * 12
    else:
        ins_month = re.search(r"(?:保|投保|就保|年資).{0,4}?(\d{1,3})\s*個?月", text)
        if ins_month:
            profile["insurance_months"] = int(ins_month.group(1))

    # 身心障礙
    if re.search(r"身心障礙|身障|殘障|障礙手冊|障礙證明", text):
        profile["has_disability_cert"] = True

    # 育有幼兒
    if re.search(r"幼兒|嬰兒|幼子|小孩還小|三歲以下|3歲以下|育兒", text):
        profile["has_young_children"] = True

    # 原住民
    if re.search(r"原住民", text):
        profile["is_indigenous"] = True

    # 受扶養眷屬人數：「扶養2人」「養3個」「撫養兩位」
    dep_match = re.search(r"(?:扶養|撫養|養).{0,3}?([一二兩三四五六七八九十\d]+)\s*(?:人|位|個|名)", text)
    if dep_match:
        n = _to_int(dep_match.group(1))
        if n is not None:
            profile["dependents_count"] = n

    # 平均月投保薪資：「投保薪資4萬」「月投保 44100」
    salary_wan = re.search(r"投保薪資.{0,3}?(\d+(?:\.\d+)?)\s*萬", text)
    if salary_wan:
        profile["avg_insured_salary"] = int(float(salary_wan.group(1)) * 10000)
    else:
        salary_raw = re.search(r"投保薪資.{0,3}?(\d{4,6})", text)
        if salary_raw:
            profile["avg_insured_salary"] = int(salary_raw.group(1))

    # 產業 / 職稱（粗略）：「在工廠」「餐廳主管」
    industry_match = re.search(r"在(.{1,8}?)(?:工作|上班|做|服務)", text)
    if industry_match:
        profile["industry"] = industry_match.group(1).strip()

    profile["missing_fields"] = compute_missing_fields(profile)
    profile["target_groups"] = derive_target_groups(profile)
    return profile
