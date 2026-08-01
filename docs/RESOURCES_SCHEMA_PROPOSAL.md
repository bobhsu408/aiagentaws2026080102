# 職涯導航家 — 新版 resources.json Schema 設計提案

> 最後更新：2026-07-29
> 目的：解決現有 schema 無法表達條件分支、金額基準類型、發給對象等問題

---

## 一、為什麼要重新設計

現有 schema 的根本問題：

| 問題 | 案例 |
|------|------|
| 無法表達條件分支 | 失業給付「一般最長 6 月 vs 45歲↑/身障最長 9 月」，現在只能寫一個數字 |
| 分不清金額基準 | 有的是「月投保薪資 × 60%」有的是「最低工資 × 60%」，現在用同一個 formula 格式 |
| 分不清發給對象 | 僱用獎助是發給**雇主**不是勞工，現在混在一起會誤導使用者 |
| 無法表達併領限制 | 「失業給付期間不得同時請領職訓津貼」這類規則無處放 |
| 缺法規引用 | 無法告訴使用者「這個數字來自哪一條法律」 |
| 缺加給機制 | 眷屬加給 10%（上限 20%）完全無法表達 |

---

## 二、新 Schema 設計

### 完整 TypeScript 型別定義

```typescript
interface Resource {
  /** 唯一識別碼，snake_case */
  id: string;

  /** 方案名稱（中文） */
  name: string;

  /** 分類 */
  category: "津貼" | "獎勵" | "訓練" | "貸款" | "補助";

  /** 發給對象 — 解決「僱用獎助發給雇主」被誤認為勞工可領的問題 */
  recipient: "勞工" | "雇主" | "事業單位";

  /** 簡述（一兩句話） */
  description: string;

  /** 資格條件 */
  eligibility: Eligibility;

  /** 給付內容（支持條件分支） */
  benefit: Benefit;

  /** 併領限制 */
  concurrency_rules: ConcurrencyRule[];

  /** 申請所需文件 */
  required_documents: string[];

  /** 申辦步驟（選填） */
  application_steps?: string[];

  /** 法規出處 */
  law_references: LawReference[];

  /** 資料來源 URL（非法規來源時使用） */
  source_url?: string;

  /** 最後人工確認日期 YYYY-MM-DD */
  last_verified: string;

  /** 備註 */
  notes?: string;
}

interface Eligibility {
  /** 年齡下限（含） */
  min_age?: number;

  /** 年齡上限（含） */
  max_age?: number;

  /** 適用對象標籤 */
  target_groups?: TargetGroup[];

  /** 是否要求非自願離職 */
  requires_involuntary_leave?: boolean;

  /** 最低保險年資（月） */
  min_insurance_months?: number;

  /** 是否要求參加全日制職訓 */
  requires_fulltime_training?: boolean;

  /** 是否要求創業計畫 */
  requires_business_plan?: boolean;

  /** 是否要求育有幼兒 */
  requires_young_children?: boolean;

  /** 是否要求身心障礙證明 */
  requires_disability_cert?: boolean;

  /** 是否要求積極求職（向就服站登記） */
  requires_active_job_search?: boolean;

  /** 是否要求育嬰留職停薪 */
  requires_parental_leave?: boolean;

  /** 其他條件（自然語言補充） */
  other_conditions?: string;
}

type TargetGroup =
  | "中高齡"      // 45-64 歲
  | "高齡"        // 65 歲以上
  | "青年"        // 15-29 歲
  | "婦女"
  | "身心障礙"
  | "原住民"
  | "外籍配偶"
  | "長期失業"    // 連續失業 1 年以上
  | "一般";

/** 給付內容：支持條件分支 */
interface Benefit {
  /** 基本給付規則（所有人適用） */
  base: BenefitTier;

  /** 條件加碼（符合特定條件時覆蓋或加給） */
  conditional_tiers?: ConditionalTier[];

  /** 加給機制（如眷屬加給） */
  surcharges?: Surcharge[];
}

interface BenefitTier {
  /** 金額類型 */
  amount_type: "formula" | "fixed" | "range" | "none";

  /**
   * 金額公式（amount_type = "formula" 時）
   * 格式："{基準} * {比例}"
   * 基準可為：avg_insured_salary | min_wage | hourly_min_wage
   */
  formula?: string;

  /** 金額基準說明（讓 Agent 能用白話解釋） */
  formula_description?: string;

  /** 固定金額（amount_type = "fixed" 時，單位：新台幣元） */
  fixed_amount?: number;

  /** 金額範圍（amount_type = "range" 時） */
  min_amount?: number;
  max_amount?: number;

  /** 發給頻率 */
  frequency: "monthly" | "one_time" | "per_occurrence" | "per_hour";

  /** 最長期間（月），0 表示一次性 */
  max_months: number;

  /** 最多次數（per_occurrence 時使用） */
  max_occurrences?: number;

  /** 每年度上限次數 */
  max_per_year?: number;
}

interface ConditionalTier {
  /** 條件描述 */
  condition: string;

  /** 條件判斷欄位（對應 Eligibility 或 profile） */
  condition_field?: string;

  /** 覆蓋的給付內容 */
  override: Partial<BenefitTier>;
}

interface Surcharge {
  /** 加給說明 */
  description: string;

  /** 每單位加給比例 */
  rate_per_unit: string;

  /** 上限 */
  max_rate: string;

  /** 適用單位（如「受扶養眷屬人數」） */
  unit: string;
}

interface ConcurrencyRule {
  /** 不得同時請領的方案 ID */
  conflicting_resource_id: string;

  /** 規則說明 */
  rule_description: string;

  /** 法規依據 */
  law_reference?: string;
}

interface LawReference {
  /** 法規名稱 */
  law_name: string;

  /** 條號 */
  article_no: string;

  /** 法規全文連結 */
  url: string;
}
```

---

## 三、範例：用新 schema 表達「失業給付」

```json
{
  "id": "unemployment_benefit",
  "name": "失業給付",
  "category": "津貼",
  "recipient": "勞工",
  "description": "非自願離職且就業保險年資滿 1 年以上者，可按月請領投保薪資 60% 之失業給付。",
  "eligibility": {
    "min_age": 15,
    "max_age": 65,
    "requires_involuntary_leave": true,
    "min_insurance_months": 12,
    "requires_active_job_search": true,
    "other_conditions": "向公立就業服務機構辦理求職登記後 14 日內仍無法推介就業或安排職業訓練"
  },
  "benefit": {
    "base": {
      "amount_type": "formula",
      "formula": "avg_insured_salary * 0.6",
      "formula_description": "離職前 6 個月平均月投保薪資的 60%",
      "frequency": "monthly",
      "max_months": 6
    },
    "conditional_tiers": [
      {
        "condition": "離職時已滿 45 歲",
        "condition_field": "age >= 45",
        "override": { "max_months": 9 }
      },
      {
        "condition": "領有身心障礙證明",
        "condition_field": "has_disability_cert == true",
        "override": { "max_months": 9 }
      }
    ],
    "surcharges": [
      {
        "description": "受扶養眷屬加給（無工作收入之父母、配偶、未成年子女或身障子女）",
        "rate_per_unit": "avg_insured_salary * 0.1",
        "max_rate": "avg_insured_salary * 0.2",
        "unit": "受扶養眷屬人數"
      }
    ]
  },
  "concurrency_rules": [
    {
      "conflicting_resource_id": "training_living_allowance_ei",
      "rule_description": "請領失業給付期間不得同時請領就業保險之職業訓練生活津貼",
      "law_reference": "就業促進津貼實施辦法 第 26 條"
    }
  ],
  "required_documents": [
    "國民身分證或有效證照正反面",
    "非自願離職證明書（或定期契約屆滿證明）",
    "勞工保險被保險人投保資料表",
    "本人名義之國內金融機構存摺封面影本",
    "身心障礙證明（如適用加長請領）",
    "受扶養眷屬相關證明（如申請加給）"
  ],
  "law_references": [
    {
      "law_name": "就業保險法",
      "article_no": "第 11 條",
      "url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0050021"
    },
    {
      "law_name": "就業保險法",
      "article_no": "第 16 條",
      "url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0050021"
    },
    {
      "law_name": "就業保險法",
      "article_no": "第 19-1 條",
      "url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0050021"
    }
  ],
  "last_verified": "2026-07-29",
  "notes": "二年內領滿給付期間者，需再等二年才能再次請領。"
}
```

---

## 四、範例：用新 schema 表達「中高齡僱用獎助」（發給雇主）

```json
{
  "id": "mid_age_employment_subsidy_employer",
  "name": "失業中高齡者及高齡者僱用獎助",
  "category": "獎勵",
  "recipient": "雇主",
  "description": "雇主僱用經就服站推介之失業中高齡者或高齡者，可按月請領僱用獎助。",
  "eligibility": {
    "min_age": 45,
    "requires_involuntary_leave": true,
    "requires_active_job_search": true,
    "other_conditions": "勞工須經公立就業服務機構推介，雇主連續僱用滿 30 日以上"
  },
  "benefit": {
    "base": {
      "amount_type": "fixed",
      "fixed_amount": 13000,
      "frequency": "monthly",
      "max_months": 12,
      "formula_description": "中高齡者（45-64歲）全時工作，每人每月 13,000 元"
    },
    "conditional_tiers": [
      {
        "condition": "受僱者為 65 歲以上高齡者",
        "condition_field": "age >= 65",
        "override": { "fixed_amount": 15000 }
      },
      {
        "condition": "非按月計酬全時工作（部分工時）",
        "override": {
          "amount_type": "formula",
          "formula": "hours * 70",
          "formula_description": "中高齡者每小時 70 元，月上限 13,000 元",
          "max_amount": 13000
        }
      },
      {
        "condition": "高齡者非按月計酬全時工作（部分工時）",
        "condition_field": "age >= 65",
        "override": {
          "amount_type": "formula",
          "formula": "hours * 80",
          "formula_description": "高齡者每小時 80 元，月上限 15,000 元",
          "max_amount": 15000
        }
      }
    ]
  },
  "concurrency_rules": [],
  "required_documents": [
    "僱用名冊",
    "在職證明",
    "勞工保險投保紀錄",
    "薪資證明"
  ],
  "law_references": [
    {
      "law_name": "失業中高齡者及高齡者就業促進辦法",
      "article_no": "第 41 條",
      "url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0090055"
    }
  ],
  "last_verified": "2026-07-29"
}
```

---

## 五、與現有 schema 的差異對照

| 面向 | 現有 schema | 新 schema |
|------|-------------|-----------|
| 金額表達 | `monthly_amount_formula: "avg_insured_salary * 0.6"` 或 `"flat:1500"` | `benefit.base.amount_type` + `formula` / `fixed_amount`，語意明確 |
| 條件分支 | 無 | `benefit.conditional_tiers[]` 可表達多組覆蓋條件 |
| 加給機制 | 無 | `benefit.surcharges[]` |
| 發給對象 | 無（全混在一起） | `recipient: "勞工" \| "雇主"` |
| 併領限制 | 無 | `concurrency_rules[]` |
| 法規出處 | 無 | `law_references[]` 含條號和 URL |
| 金額基準 | 無法區分投保薪資 vs 最低工資 | formula 中明確寫 `avg_insured_salary` 或 `min_wage` |
| 資料時效 | 無 | `last_verified` |
| 期限上限 | `max_months` 只有一個值 | base 有一個值，conditional_tiers 可覆蓋 |

---

## 六、對 career_tools.py 的影響

### `match_resources` — 需小幅調整

新增 `recipient` 過濾：預設只回傳 `recipient: "勞工"` 的方案。若使用者明確問「雇主可以拿什麼補助」再回傳雇主的。

### `calculate_benefit` — 需中幅重寫

- 原本只看 `monthly_amount_formula`，改為讀 `benefit.base` + 檢查 `conditional_tiers`
- 新增：根據使用者 profile 選擇適用的 tier
- 新增：計算 surcharge（眷屬加給）
- 新增：檢查 `concurrency_rules` 並在回傳中標示

### `get_checklist` — 幾乎不變

`required_documents` 欄位名稱和結構不變。

### `generate_roadmap` — 不變

讀 `max_months` 的路徑改一下即可。

---

## 七、遷移計畫

1. **先寫新 schema 的 JSON 檔**（新檔名 `resources_v2.json`），不動舊檔
2. **改寫 `career_tools.py`** 讀新格式
3. **測試通過後**刪除舊 `resources.json`，重新命名
4. 逐步擴充至 20~30 筆

建議不要一步到位全改，先確保 6 步驟 pipeline 用新格式跑通一個 case，再擴資料。

---

## 八、全局常數檔（建議新增）

部分金額基準會年度更新，建議抽出為獨立設定：

```json
// data/constants.json
{
  "year": 2026,
  "monthly_min_wage": 28590,
  "hourly_min_wage": 190,
  "postal_2yr_rate": 0.015,
  "last_updated": "2026-01-01",
  "source": "勞動部 114 年 10 月 25 日公告"
}
```

`calculate_benefit` 計算時從此檔讀取 `min_wage`，而非硬編碼。
