"""六步驟 Career Tools — 純業務邏輯

此模組不依賴 strands，僅實作六步驟的計算與資料處理邏輯，
方便獨立單元測試。career_tools.py 以 @tool 薄封裝呼叫這裡的函式。

    1. analyze_profile   — 解析自然語言為結構化 profile
    2. match_resources   — 比對 profile 與 resources.json 的 eligibility
    3. calculate_benefit — 依 benefit 公式 / 條件分支 / 加給試算金額
    4. generate_roadmap  — 產出時間軸行動計畫（含課程提示）
    5. get_checklist     — 彙整應備文件清單
    6. send_notification — 模擬通知（展示用 email，保留 LINE 擴充位）

所有金額公式與條件式均透過 formula 模組的白名單求值，不使用內建 eval。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from .data_loader import (
    get_resource_by_id,
    load_constants,
    load_courses,
    load_resources,
)
from .formula import evaluate_condition, evaluate_formula, find_missing_variables
from .profile import derive_target_groups, extract_profile

# 台灣時區（UTC+8）
_TZ_TAIPEI = timezone(timedelta(hours=8))

# 缺值時可用基本工資作保守下限替代的變數
_MIN_WAGE_SUBSTITUTABLE = {"avg_insured_salary"}


# ============================================================================
# 共用輔助
# ============================================================================
def build_formula_context(profile: dict) -> dict[str, Any]:
    """由 profile + constants 組出公式 / 條件求值用的變數 context。

    Args:
        profile: 使用者 profile

    Returns:
        變數名 → 值的對應（缺的欄位為 None）。
    """
    constants = load_constants()
    return {
        "avg_insured_salary": profile.get("avg_insured_salary"),
        "min_wage": constants.get("monthly_min_wage"),
        "hourly_min_wage": constants.get("hourly_min_wage"),
        "monthly_rent": profile.get("monthly_rent"),
        "hours": profile.get("monthly_work_hours"),
        "remaining_unemployment_benefit": profile.get("remaining_unemployment_benefit"),
        "age": profile.get("age"),
        "has_disability_cert": bool(profile.get("has_disability_cert", False)),
        "insurance_status": profile.get("insurance_status"),
        "dependents_count": profile.get("dependents_count", 0) or 0,
    }


# ============================================================================
# Tool 1：analyze_profile
# ============================================================================
def analyze_profile(user_description: str) -> dict:
    """解析使用者自然語言描述，萃取結構化背景資料。

    Args:
        user_description: 使用者用自然語言描述的個人狀況

    Returns:
        含 profile、missing_fields、target_groups、guidance 的 dict。
    """
    profile = extract_profile(user_description or "")
    missing = profile.get("missing_fields", [])

    field_labels = {
        "age": "年齡",
        "leave_reason": "離職原因（是否為資遣、關廠等非自願離職）",
        "insurance_months": "就業保險年資（投保多久）",
    }
    guidance = (
        "資料已足夠，可以進行資源匹配。"
        if not missing
        else "尚需向使用者確認：" + "、".join(field_labels.get(f, f) for f in missing)
    )

    return {
        "status": "ok",
        "profile": profile,
        "missing_fields": missing,
        "target_groups": profile.get("target_groups", []),
        "guidance": guidance,
    }


# ============================================================================
# Tool 2：match_resources
# ============================================================================
def check_eligibility(profile: dict, resource: dict) -> dict:
    """檢查單一方案對此 profile 的資格符合度。

    Args:
        profile: 使用者 profile
        resource: 單一補助方案

    Returns:
        含 status、unmet_conditions、missing_info、info_conditions 的 dict。
        status ∈ {eligible, likely, needs_info, excluded}
    """
    elig = resource.get("eligibility", {})
    unmet: list[str] = []
    missing: list[str] = []
    info: list[str] = []

    age = profile.get("age")
    if "min_age" in elig:
        if age is None:
            missing.append("年齡")
        elif age < elig["min_age"]:
            unmet.append(f"年齡需滿 {elig['min_age']} 歲")
    if "max_age" in elig:
        if age is None:
            if "年齡" not in missing:
                missing.append("年齡")
        elif age > elig["max_age"]:
            unmet.append(f"年齡需在 {elig['max_age']} 歲以下")

    if "min_insurance_months" in elig:
        ins = profile.get("insurance_months")
        if ins is None:
            missing.append("就業保險年資")
        elif ins < elig["min_insurance_months"]:
            unmet.append(f"就業保險年資需滿 {elig['min_insurance_months']} 個月")

    if elig.get("requires_involuntary_leave"):
        reason = profile.get("leave_reason")
        if reason is None:
            missing.append("離職原因")
        elif reason != "非自願":
            unmet.append("須為非自願離職（資遣、關廠、契約屆滿等）")

    if elig.get("requires_disability_cert") and not profile.get("has_disability_cert"):
        unmet.append("須持有身心障礙證明")

    if elig.get("requires_young_children") and not profile.get("has_young_children"):
        unmet.append("須育有幼兒")

    if elig.get("requires_parental_leave") and profile.get("leave_reason") != "育嬰":
        unmet.append("須為育嬰留職停薪")

    if elig.get("requires_fulltime_training"):
        info.append("需確認是否願意參加全日制職業訓練")
    if elig.get("requires_business_plan"):
        info.append("需確認是否有創業計畫")

    target_groups = elig.get("target_groups")
    if target_groups:
        user_groups = set(derive_target_groups(profile))
        if not user_groups.intersection(set(target_groups)):
            unmet.append(f"適用對象為：{', '.join(target_groups)}")

    if unmet:
        status = "excluded"
    elif missing:
        status = "needs_info"
    elif info:
        status = "likely"
    else:
        status = "eligible"

    return {
        "status": status,
        "unmet_conditions": unmet,
        "missing_info": missing,
        "info_conditions": info,
    }


def match_resources(profile: dict, include_employer: bool = False) -> dict:
    """根據使用者 profile 匹配符合資格的補助方案。

    Args:
        profile: 由 analyze_profile 產出的結構化背景
        include_employer: 是否納入發給雇主的方案（預設 False）

    Returns:
        含 matched、excluded、concurrency_warnings、total_matched 的 dict。
    """
    resources = load_resources()
    matched: list[dict] = []
    excluded: list[dict] = []
    concurrency_warnings: list[str] = []

    for res in resources:
        recipient = res.get("recipient", "勞工")
        if recipient != "勞工" and not include_employer:
            excluded.append({
                "id": res.get("id"),
                "name": res.get("name"),
                "reason": f"發給對象為「{recipient}」，非勞工直接申請",
            })
            continue

        check = check_eligibility(profile, res)
        entry = {
            "id": res.get("id"),
            "name": res.get("name"),
            "category": res.get("category"),
            "recipient": recipient,
            "match_status": check["status"],
            "unmet_conditions": check["unmet_conditions"],
            "missing_info": check["missing_info"],
            "info_conditions": check["info_conditions"],
            "description": res.get("description"),
        }

        if check["status"] == "excluded":
            excluded.append({
                "id": res.get("id"),
                "name": res.get("name"),
                "reason": "；".join(check["unmet_conditions"]),
            })
            continue

        for rule in res.get("concurrency_rules", []):
            warn = rule.get("rule_description")
            if warn and warn not in concurrency_warnings:
                concurrency_warnings.append(warn)

        matched.append(entry)

    return {
        "status": "ok",
        "matched": matched,
        "excluded": excluded,
        "concurrency_warnings": concurrency_warnings,
        "total_matched": len(matched),
        "notes": "match_status：eligible=符合、likely=符合但需確認行動意願、needs_info=待補資料。以上依目前提供的資訊判斷，實際資格以主管機關核定為準。",
    }


# ============================================================================
# Tool 3：calculate_benefit
# ============================================================================
def resolve_tier(tier: dict, ctx: dict, min_wage: int) -> dict:
    """求值單一給付 tier 的金額。

    Args:
        tier: 給付 tier（base 或套用 override 後的結果）
        ctx: 公式變數 context
        min_wage: 當年度基本工資（保守替代用）

    Returns:
        含金額、公式、缺值資訊、假設的 dict。
    """
    amount_type = tier.get("amount_type", "none")
    out: dict[str, Any] = {"amount_type": amount_type}

    if "max_months" in tier:
        out["max_months"] = tier["max_months"]
    if "frequency" in tier:
        out["frequency"] = tier["frequency"]

    if amount_type == "fixed":
        out["monthly_amount"] = tier.get("fixed_amount")

    elif amount_type == "range":
        out["min_amount"] = tier.get("min_amount")
        out["max_amount"] = tier.get("max_amount")
        out["formula_description"] = tier.get("formula_description")

    elif amount_type == "formula":
        formula = tier.get("formula", "")
        out["formula"] = formula
        out["formula_description"] = tier.get("formula_description")
        if "max_amount" in tier:
            out["cap"] = tier["max_amount"]

        val = evaluate_formula(formula, ctx)
        if val is not None:
            amount = round(val)
            if "max_amount" in tier:
                amount = min(amount, tier["max_amount"])
            out["monthly_amount"] = amount
        else:
            missing = find_missing_variables(formula, ctx)
            out["needs_input"] = missing
            cons_ctx = dict(ctx)
            substituted = []
            for m in missing:
                if m in _MIN_WAGE_SUBSTITUTABLE:
                    cons_ctx[m] = min_wage
                    substituted.append(m)
            if substituted:
                cons_val = evaluate_formula(formula, cons_ctx)
                if cons_val is not None:
                    amount = round(cons_val)
                    if "max_amount" in tier:
                        amount = min(amount, tier["max_amount"])
                    out["conservative_monthly_amount"] = amount
                    out["assumption"] = (
                        f"缺少實際數值，暫以基本工資 {min_wage:,} 元代入 "
                        f"{', '.join(substituted)} 作為保守下限估算"
                    )

    return out


def apply_conditional_tiers(base: dict, tiers: list[dict], ctx: dict) -> tuple[dict, list[str]]:
    """依 profile 套用符合的 conditional_tiers（覆蓋 base）。

    Args:
        base: benefit.base
        tiers: benefit.conditional_tiers
        ctx: 條件求值 context

    Returns:
        (套用後的有效 tier, 已套用的條件描述清單)
    """
    effective = dict(base)
    applied: list[str] = []
    for ct in tiers:
        cond = ct.get("condition_field")
        verdict = evaluate_condition(cond, ctx) if cond else None
        if verdict is True:
            effective.update(ct.get("override", {}))
            applied.append(ct.get("condition", cond))
    return effective, applied


def compute_surcharges(surcharges: list[dict], ctx: dict) -> dict | None:
    """計算加給（如眷屬加給）。

    Args:
        surcharges: benefit.surcharges
        ctx: 公式變數 context

    Returns:
        加給明細 dict，或 None（無加給 / 無法計算）。
    """
    dep = ctx.get("dependents_count", 0) or 0
    if not surcharges or dep <= 0:
        return None
    s = surcharges[0]
    per_unit = evaluate_formula(s.get("rate_per_unit", ""), ctx)
    cap = evaluate_formula(s.get("max_rate", ""), ctx)
    if per_unit is None:
        return {
            "description": s.get("description"),
            "needs_input": find_missing_variables(s.get("rate_per_unit", ""), ctx),
            "note": "缺少投保薪資，無法計算眷屬加給金額",
        }
    monthly = per_unit * dep
    if cap is not None:
        monthly = min(monthly, cap)
    return {
        "description": s.get("description"),
        "unit_count": dep,
        "monthly_surcharge": round(monthly),
    }


def calculate_benefit(matched_ids: list[str], profile: dict) -> dict:
    """試算使用者可領取的金額。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        含 calculations、concurrency_notes、disclaimer 的 dict。
    """
    constants = load_constants()
    min_wage = constants.get("monthly_min_wage", 29500)
    ctx = build_formula_context(profile)

    calculations: list[dict] = []
    concurrency_notes: list[str] = []

    for rid in matched_ids:
        res = get_resource_by_id(rid)
        if res is None:
            calculations.append({"resource_id": rid, "error": "查無此方案"})
            continue

        benefit = res.get("benefit", {})
        base = benefit.get("base", {})
        effective, applied = apply_conditional_tiers(
            base, benefit.get("conditional_tiers", []), ctx
        )
        resolved = resolve_tier(effective, ctx, min_wage)

        calc: dict[str, Any] = {
            "resource_id": rid,
            "resource_name": res.get("name"),
            "applied_tiers": applied,
            **resolved,
        }

        surcharge = compute_surcharges(benefit.get("surcharges", []), ctx)
        if surcharge:
            calc["surcharge"] = surcharge

        monthly = resolved.get("monthly_amount") or resolved.get("conservative_monthly_amount")
        months = resolved.get("max_months", 0)
        if monthly and resolved.get("frequency") == "monthly" and months:
            sur_monthly = 0
            if surcharge and "monthly_surcharge" in surcharge:
                sur_monthly = surcharge["monthly_surcharge"]
            total = (monthly + sur_monthly) * months
            calc["estimated_total"] = total
            if resolved.get("conservative_monthly_amount") and not resolved.get("monthly_amount"):
                calc["estimated_total_note"] = "此為保守下限估算，實際依投保薪資而定"

        calc["law_references"] = res.get("law_references", [])

        for rule in res.get("concurrency_rules", []):
            note = rule.get("rule_description")
            if note and note not in concurrency_notes:
                concurrency_notes.append(note)

        calculations.append(calc)

    return {
        "status": "ok",
        "calculations": calculations,
        "concurrency_notes": concurrency_notes,
        "min_wage_used": min_wage,
        "disclaimer": "以上為試算結果，實際金額以勞保局 / 主管機關核定為準。",
    }


# ============================================================================
# Tool 4：generate_roadmap
# ============================================================================
def match_courses(profile: dict) -> list[dict]:
    """從 courses.json 篩出符合使用者年齡與族群的課程。

    Args:
        profile: 使用者 profile

    Returns:
        符合的課程摘要清單。
    """
    age = profile.get("age")
    user_groups = set(derive_target_groups(profile))
    out: list[dict] = []
    for c in load_courses():
        ta = c.get("target_age", {})
        min_a, max_a = ta.get("min"), ta.get("max")
        if age is not None:
            if min_a is not None and age < min_a:
                continue
            if max_a is not None and age > max_a:
                continue
        groups = set(c.get("target_groups", []))
        if groups and user_groups and not groups.intersection(user_groups):
            continue
        out.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "provider": c.get("provider"),
            "cost": c.get("cost", {}).get("detail"),
            "linked_resource_id": c.get("linked_resource_id"),
            "source_url": c.get("source_url"),
        })
    return out


def generate_roadmap(matched_ids: list[str], profile: dict) -> dict:
    """產出 1~6 個月的時間軸行動計畫。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表
        profile: 使用者背景資料

    Returns:
        含 timeline、decision_points、courses、total_months 的 dict。
    """
    ids = set(matched_ids)
    has_unemployment = "unemployment_benefit" in ids
    has_training = "training_living_allowance" in ids
    has_early_bonus = "early_reemployment_bonus" in ids
    has_relocation = bool(ids.intersection({
        "relocation_transport_subsidy",
        "relocation_moving_subsidy",
        "relocation_rent_subsidy",
    }))

    target_industry = profile.get("target_industry")
    search_keywords = [target_industry] if target_industry else ["中高齡轉職", "數位技能", "照顧服務"]

    timeline: list[dict] = []
    decision_points: list[str] = []

    m0 = {"month": 0, "label": "離職當週", "actions": []}
    if has_unemployment:
        m0["actions"].append({
            "action": "向住居所在地公立就業服務站辦理求職登記",
            "priority": "必要",
            "related_resource": "unemployment_benefit",
        })
        m0["actions"].append({
            "action": "向前雇主索取「非自願離職證明書」（雇主應依法開立）",
            "priority": "必要",
            "related_resource": "unemployment_benefit",
        })
    if not m0["actions"]:
        m0["actions"].append({"action": "整理個人資歷與求職方向", "priority": "建議"})
    timeline.append(m0)

    m1 = {"month": 1, "label": "第 1 個月", "actions": []}
    if has_unemployment:
        m1["actions"].append({
            "action": "求職登記後 14 日內若無法推介就業或安排職訓，開始請領失業給付",
            "priority": "里程碑",
            "related_resource": "unemployment_benefit",
        })
    if has_training:
        m1["actions"].append({
            "action": "評估是否參加全日制職業訓練，建立第二專長",
            "priority": "決策點",
            "related_resource": "training_living_allowance",
            "course_hint": {
                "type": "suggested_search",
                "keywords": search_keywords,
                "search_via": "exa_mcp",
                "note": "實際開課梯次、報名截止日於對話中即時查詢",
            },
        })
        decision_points.append(
            "第 1 個月需決定：繼續領失業給付積極求職，或轉為參加全日制職訓（兩者不得同時請領，須擇一）"
        )
    timeline.append(m1)

    m23 = {"month": 2, "label": "第 2～3 個月", "actions": []}
    if has_training:
        m23["actions"].append({
            "action": "若已入訓，專注受訓並按月領取職業訓練生活津貼",
            "priority": "進行中",
            "related_resource": "training_living_allowance",
        })
    m23["actions"].append({"action": "持續投遞履歷、參加就服站推介面試", "priority": "建議"})
    if has_relocation:
        m23["actions"].append({
            "action": "若鎖定跨區職缺，先確認異地就業交通/租屋/搬遷補助資格",
            "priority": "建議",
            "related_resource": "relocation_transport_subsidy",
        })
    timeline.append(m23)

    m46 = {"month": 4, "label": "第 4～6 個月", "actions": []}
    if has_early_bonus:
        m46["actions"].append({
            "action": "若提早找到工作並就保滿 3 個月，申請提早就業獎助津貼（未領完失業給付的 50%）",
            "priority": "里程碑",
            "related_resource": "early_reemployment_bonus",
        })
    if has_relocation:
        m46["actions"].append({
            "action": "跨區就任後，按月檢附證明申請異地就業補助",
            "priority": "進行中",
            "related_resource": "relocation_transport_subsidy",
        })
    m46["actions"].append({"action": "穩定就業，視情況規劃在職進修", "priority": "建議"})
    timeline.append(m46)

    return {
        "status": "ok",
        "timeline": timeline,
        "decision_points": decision_points,
        "courses": {
            "curated": match_courses(profile),
            "hint": {
                "keywords": search_keywords,
                "search_via": "exa_mcp",
                "note": "curated 為計畫層級穩定資料；即時開課清單建議透過即時搜尋補充。",
            },
        },
        "total_months": 6,
    }


# ============================================================================
# Tool 5：get_checklist
# ============================================================================
_DOC_HOW_TO_GET: dict[str, str] = {
    "國民身分證或有效證照正反面": "本人持有即可，必要時至戶政事務所補辦",
    "非自願離職證明書（或定期契約屆滿證明）": "向前雇主索取，雇主應依規定開立",
    "非自願離職證明書": "向前雇主索取，雇主應依規定開立",
    "勞工保險（就業保險）被保險人投保資料表": "至勞保局 e 化服務系統或臨櫃列印",
    "勞工保險被保險人投保資料表": "至勞保局 e 化服務系統或臨櫃列印",
    "本人名義之國內金融機構存摺封面影本": "任一本人名下銀行/郵局帳戶存摺封面",
}


def get_checklist(matched_ids: list[str]) -> dict:
    """回傳申請各補助方案所需的文件清單（去重、分類）。

    Args:
        matched_ids: 匹配到的補助方案 ID 列表

    Returns:
        含 common_documents、per_resource、tips 的 dict。
    """
    doc_count: dict[str, int] = {}
    per_resource_raw: list[tuple[str, str, list[str]]] = []

    for rid in matched_ids:
        res = get_resource_by_id(rid)
        if res is None:
            continue
        docs = res.get("required_documents", [])
        per_resource_raw.append((rid, res.get("name", rid), docs))
        for d in docs:
            doc_count[d] = doc_count.get(d, 0) + 1

    common_docs = [d for d, n in doc_count.items() if n >= 2]

    common_documents = [
        {"document": d, "how_to_get": _DOC_HOW_TO_GET.get(d, "依主管機關要求備妥")}
        for d in common_docs
    ]

    per_resource: list[dict] = []
    for rid, name, docs in per_resource_raw:
        specific = [d for d in docs if d not in common_docs]
        per_resource.append({
            "resource_id": rid,
            "resource_name": name,
            "specific_documents": [
                {"document": d, "how_to_get": _DOC_HOW_TO_GET.get(d, "依主管機關要求備妥")}
                for d in specific
            ],
        })

    return {
        "status": "ok",
        "common_documents": common_documents,
        "per_resource": per_resource,
        "tips": [
            "建議先備妥通用文件，到就業服務站可一次辦理多項申請。",
            "若雇主拒發非自願離職證明，可向當地勞工行政主管機關申請認定或協助。",
        ],
        "note": "文件取得方式為一般性指引，實際應備文件以各方案受理單位公告為準。",
    }


# ============================================================================
# Tool 6：send_notification
# ============================================================================
def send_notification(summary: str, email: str = "", line_user_id: str = "") -> dict:
    """傳送行動計畫摘要通知（展示模式）。

    Args:
        summary: 行動計畫摘要文字
        email: 收件 email（展示用）
        line_user_id: LINE 使用者 ID（保留擴充，目前未啟用）

    Returns:
        含 status、channel、demo_mode、sent_at 的 dict。
    """
    sent_at = datetime.now(_TZ_TAIPEI).isoformat(timespec="seconds")
    target = email or "（未提供 email）"
    return {
        "status": "success",
        "channel": "email",
        "delivered": False,
        "demo_mode": True,
        "recipient": target,
        "sent_at": sent_at,
        "message": f"（示範模式）已將行動計畫摘要寄送至 {target}",
        "summary_preview": (summary or "")[:200],
        "note": "示範模式未實際寄出；正式版可接入 AWS SES（email）或 LINE Messaging API（推播）。",
    }
