"""六步驟 Career Tools 單元測試

以情境 A（58 歲工廠作業員因自動化被資遣）為主軸，驗證六個 tool 的
純邏輯（tools.logic）回傳合理。不依賴 strands。
"""

import os
import sys

# 將 app/careernav 加入 import 路徑（tests 的上一層）
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import pytest

from tools import data_loader, logic
from tools.formula import evaluate_condition, evaluate_formula, find_missing_variables


@pytest.fixture(autouse=True)
def _clear_cache():
    """每次測試前清資料快取，確保讀到最新檔案。"""
    data_loader.clear_cache()
    yield
    data_loader.clear_cache()


# ----------------------------------------------------------------------------
# formula 模組
# ----------------------------------------------------------------------------
def test_evaluate_formula_basic():
    assert evaluate_formula("avg_insured_salary * 0.6", {"avg_insured_salary": 45000}) == 27000.0


def test_evaluate_formula_missing_var_returns_none():
    assert evaluate_formula("avg_insured_salary * 0.6", {"avg_insured_salary": None}) is None


def test_evaluate_formula_rejects_unsafe():
    # 不允許函式呼叫等語法
    assert evaluate_formula("__import__('os').system('ls')", {}) is None


def test_evaluate_condition_true_false_and_missing():
    assert evaluate_condition("age >= 45", {"age": 58}) is True
    assert evaluate_condition("age >= 45", {"age": 30}) is False
    assert evaluate_condition("has_disability_cert == true", {"has_disability_cert": True}) is True
    # 缺變數 → None（待確認）
    assert evaluate_condition("age >= 45", {"age": None}) is None


def test_find_missing_variables():
    missing = find_missing_variables("avg_insured_salary * 0.6", {"avg_insured_salary": None})
    assert "avg_insured_salary" in missing


# ----------------------------------------------------------------------------
# Tool 1：analyze_profile
# ----------------------------------------------------------------------------
def test_analyze_profile_scenario_a():
    result = logic.analyze_profile("我58歲，在工廠工作，上個月被資遣，就保保了20年")
    profile = result["profile"]
    assert profile["age"] == 58
    assert profile["leave_reason"] == "非自願"
    assert profile["insurance_months"] == 240
    assert "中高齡" in result["target_groups"]
    # 關鍵欄位齊全 → 無 missing
    assert result["missing_fields"] == []


def test_analyze_profile_reports_missing():
    result = logic.analyze_profile("我想找工作")
    assert "age" in result["missing_fields"]
    assert result["guidance"].startswith("尚需")


# ----------------------------------------------------------------------------
# Tool 2：match_resources
# ----------------------------------------------------------------------------
def _scenario_a_profile():
    return logic.analyze_profile(
        "我58歲，在工廠工作，上個月被資遣，就保保了20年"
    )["profile"]


def test_match_resources_scenario_a():
    result = logic.match_resources(_scenario_a_profile())
    ids = {m["id"] for m in result["matched"]}
    # 失業給付、提早就業獎助應在符合清單
    assert "unemployment_benefit" in ids
    assert "early_reemployment_bonus" in ids
    # 職訓生活津貼需確認受訓意願 → likely
    training = next(m for m in result["matched"] if m["id"] == "training_living_allowance")
    assert training["match_status"] == "likely"
    # 有併領警告
    assert any("失業給付" in w for w in result["concurrency_warnings"])


def test_match_resources_young_excluded_by_insurance():
    # 就保年資不足者，失業給付應被排除
    profile = logic.analyze_profile("我25歲，被資遣，就保只保了3個月")["profile"]
    result = logic.match_resources(profile)
    excluded_ids = {e["id"] for e in result["excluded"]}
    assert "unemployment_benefit" in excluded_ids


# ----------------------------------------------------------------------------
# Tool 3：calculate_benefit
# ----------------------------------------------------------------------------
def test_calculate_benefit_with_salary_and_age_over_45():
    profile = _scenario_a_profile()
    profile["avg_insured_salary"] = 45000
    result = logic.calculate_benefit(["unemployment_benefit"], profile)
    calc = result["calculations"][0]
    # 45 歲以上 → 套用 9 個月 tier
    assert calc["max_months"] == 9
    # 月投保薪資 45000 * 0.6 = 27000
    assert calc["monthly_amount"] == 27000
    assert calc["estimated_total"] == 27000 * 9
    assert calc["law_references"]


def test_calculate_benefit_missing_salary_uses_conservative():
    profile = _scenario_a_profile()  # 無 avg_insured_salary
    result = logic.calculate_benefit(["unemployment_benefit"], profile)
    calc = result["calculations"][0]
    assert "needs_input" in calc
    assert "avg_insured_salary" in calc["needs_input"]
    # 以基本工資保守估算
    assert "conservative_monthly_amount" in calc
    assert "assumption" in calc


def test_calculate_benefit_surcharge_for_dependents():
    profile = _scenario_a_profile()
    profile["avg_insured_salary"] = 45000
    profile["dependents_count"] = 2
    result = logic.calculate_benefit(["unemployment_benefit"], profile)
    calc = result["calculations"][0]
    assert "surcharge" in calc
    # 眷屬加給每人 10%，2 人 = 20%，上限 20% → 45000*0.2 = 9000
    assert calc["surcharge"]["monthly_surcharge"] == 9000


# ----------------------------------------------------------------------------
# Tool 4：generate_roadmap
# ----------------------------------------------------------------------------
def test_generate_roadmap_has_decision_point_and_courses():
    profile = _scenario_a_profile()
    matched = ["unemployment_benefit", "training_living_allowance", "early_reemployment_bonus"]
    result = logic.generate_roadmap(matched, profile)
    assert result["total_months"] == 6
    assert result["decision_points"]  # 有擇一決策點
    # 課程 curated 不應含限青年的產業新尖兵
    curated_ids = {c["id"] for c in result["courses"]["curated"]}
    assert "industry_elite_pioneer_youth" not in curated_ids
    assert "preemployment_training_free" in curated_ids


# ----------------------------------------------------------------------------
# Tool 5：get_checklist
# ----------------------------------------------------------------------------
def test_get_checklist_dedup_common():
    matched = ["unemployment_benefit", "training_living_allowance"]
    result = logic.get_checklist(matched)
    common_docs = {c["document"] for c in result["common_documents"]}
    # 身分證與存摺封面兩案共用 → 應在通用文件
    assert any("身分證" in d for d in common_docs)
    assert len(result["per_resource"]) == 2


# ----------------------------------------------------------------------------
# Tool 6：send_notification
# ----------------------------------------------------------------------------
def test_send_notification_demo_mode():
    result = logic.send_notification("你的行動計畫摘要...", email="user@example.com")
    assert result["status"] == "success"
    assert result["demo_mode"] is True
    assert result["channel"] == "email"
    assert "user@example.com" in result["recipient"]
